$(document).ready(function() {
    
    fetch(url + "/api/poll/" + String(poll_id)).then(function(response) {
        return(response.json());
    }).then(function(json) {
        let count = json["votes_count"];
        let options = json["options"];
        let days = {};
        Object.keys(options).forEach(function(day) {
            formattedDay = moment(day).format("MMM Do YYYY");
            if(formattedDay in Object.keys(days)) {
                days[formattedDay] += parseInt(options[day])
            } else {
                days[formattedDay] = parseInt(options[day]);  
            }
        });

        $(".graph").append("<span class='graphRowLabel'>100</span>");
        $(".graph").append("<span class='graphRowLabel'>90</span>");
        $(".graph").append("<span class='graphRowLabel'>80</span>");
        $(".graph").append("<span class='graphRowLabel'>70</span>");
        $(".graph").append("<span class='graphRowLabel'>60</span>");
        $(".graph").append("<span class='graphRowLabel'>50</span>");
        $(".graph").append("<span class='graphRowLabel'>40</span>");
        $(".graph").append("<span class='graphRowLabel'>30</span>");
        $(".graph").append("<span class='graphRowLabel'>20</span>");
        $(".graph").append("<span class='graphRowLabel'>10</span>");
    

        Object.keys(days).forEach(function(day) {
            let adjustedCount = (days[day] / count);
            adjustedCount = adjustedCount * 100;
            let barDiv = document.createElement("div");
            
            barDiv.className += "graphBar ";
            barDiv.className += "h" + adjustedCount;
            
        
            document.getElementsByClassName("graph")[0].appendChild(barDiv);
        });

        $(".graph").append("<span><sup>Y </sup>&frasl;<sub> X</sub></span>");


        Object.keys(days).forEach(function(day) {
            let adjustedCount = (days[day] / count);
            adjustedCount = adjustedCount * 100;
    
            let labelSpan = document.createElement("span");

            labelSpan.className += "graphColumnLabel";
            labelSpan.innerHTML = day;

            document.getElementsByClassName("graph")[0].appendChild(labelSpan);
        });
        Object.keys(options).forEach(function(option, i) {
            let result = document.createElement("h2");
            
            let span = "<span id = " + i + "></span>"

            result.innerHTML = moment(String(option)).format("dddd, MMMM Do YYYY, h:mm:ss a") + " : " + span;
    
    
            document.getElementById("results").append(result);
            voteCounter(options[option], i);




        }); 
    });
});


function voteCounter(votes, id) {
    let current = -1;
    let timer = setInterval(function() {
        current++;
        document.getElementById(id).textContent =  current;
        if(current == votes) {
            clearInterval(timer);
        }
    }, 100);
}