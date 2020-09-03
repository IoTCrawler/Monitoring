
//document.getElementById('subscriptiontype').addEventListener("change", updateSubscription);
function updateSubscription(id, endpoint) {
    let subscription = document.getElementById('subscription');
    let subscriptiontype = $("#subscriptiontype option:selected").text();
    let filename = "";
    switch(subscriptiontype) {
        case "Stream":
            filename = 'json/subscription_iotstream.json';
            break;
        case "StreamObservation":
            filename = 'json/subscription_streamobservation.json';
            break;
        case "Sensor":
            filename = 'json/subscription_sensor.json';
            break;
        case "ObservableProperty":
            filename = 'json/subscription_observableproperty.json';
            break;
        default:
            filename = 'json/subscription_iotstream.json';
    }
    $.getJSON(filename, function(json){
        json['id'] = json['id'] + id;
        json['notification']['endpoint']['uri'] = endpoint;
        subscription.innerText = JSON.stringify(json, undefined, 2);
    });
}

$(document).ready(function() {
    $('#subscriptions').DataTable();
} );