library(geoR)

# Fetch command line arguments
myArgs <- commandArgs(trailingOnly = TRUE)
data <- myArgs[1]
locations <- myArgs[2]
model <- myArgs[3]

data <- read.table(text = data)
locations <- read.table(text = locations)

# print(data)
# print(locations)

modelo <- switch(model, "lineal" = "linear", "pepita" = "pure.nugget", "esferico" = "spherical", "exponencial" = "exponential", "gausiano" = "gaussian")
locations <- locations[1:nrow(data),2:3]

while(nrow(data) < 4){
  locations <- rbind(locations, locations[nrow(locations),] + 0.001)
  data <- rbind(data, data[nrow(data),] + 0.001)
}

tablaRes <- matrix(0, nrow = ncol(data), ncol = 3)

distancias <- dist(locations)
ordenados <- sort(distancias)

diametro = 0
for (j in 1:(nrow(locations)-1)) {
  diametro = max(diametro, ordenados[j+1]-ordenados[j])
}

diametro = round(diametro+0.5)

limiteSup = diametro
cont = 1;
while (limiteSup < max(ordenados)){
  limiteSup = diametro*cont;
  cont = cont+1;
}

for(i in 1:ncol(data)){
  tabla <- data.frame(cbind(locations$X1,locations$X2))
  tabla <- data.frame(cbind(tabla, data[i]))
  
  df = as.geodata(obj = tabla, coords.col = c(1,2), data.col = 3)
  
  geodat.v1 <- variog(df, max.dist = (summary(df)$distances.summary[2])/2, breaks = seq(0, limiteSup, diametro)[1:round(3/4*length( seq(0, limiteSup, diametro)))], option = 'bin', messages = FALSE)
  
  geoExp <- variofit(geodat.v1, nugget = 0, fix.nugget = FALSE, cov.model = modelo, messages = FALSE)
  
  tablaRes[i,1] = geoExp$nugget+geoExp[[2]][1]
  tablaRes[i,2] = geoExp$practicalRange
  tablaRes[i,3] = geoExp$nugget
}

bp <- boxplot(tablaRes[,3])
outliers <-bp$out
index3 <- which(tablaRes[,3] %in% outliers)

bp <- boxplot(tablaRes[,2])
outliers <-bp$out
index2 <- which(tablaRes[,2] %in% outliers)

bp <- boxplot(tablaRes[,1])
outliers <-bp$out
index1 <- which(tablaRes[,1] %in% outliers)

indices <- c(index1, index2, index3)
indices <- indices[!duplicated(indices)]

buenos <- setdiff(1:nrow(tablaRes),indices)
finales <- tablaRes[buenos,1:3]

cat(paste(mean(finales[,1]), mean(finales[,2]), mean(finales[,3])))

