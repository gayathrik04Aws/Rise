
/**
 * Created by anye on 1/26/16.
 */
function addEmailBox(){
    var parent = $("#emailList");
    var num_children = parent[0].childElementCount;
    var new_element="<input type=\"text\" alt=\"Email address\" id=\"email_" + num_children + "\" placeholder=\"Email Address\"/>"
    parent.append(new_element);
}


function sendInvitations(url){
    var parent = $("#emailList");
    var num_children = parent[0].childElementCount;
    var errors = "";
    var email_list =""

    for(var i=0;i<num_children;i++){
        //validate emails
        var box = $("#email_"+i)[0];
        if (box.value.length > 0) {
            var str = box.value;
            var email = str.match(/([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+)/gi);
            var ok = validateEmail(email);
            if (!ok) {
                errors = errors + box.value + " is not a valid email address.<br>";
            } else {
                if (i > 0) {
                    email_list = email_list + ";";
                }
                email_list = email_list + email;
            }
        }
        $(".email-share .button").removeClass("sending");
    }
    if (errors.length > 0){
        $("#emailErrors").html(errors);
        $(".email-share .button").removeClass("sending");
        if ($("#emailErrors").hasClass("hidden")) {
            $("#emailErrors").removeClass("hidden");
            $(".email-share .button").removeClass("sending");
        }
        if (!$("#emailErrors").hasClass("error-message")) {
            $("#emailErrors").addClass("error-message");
            $(".email-share .button").removeClass("sending");
        }
        return false;
    }
    else if (email_list.length > 0) {
       if (!$("#emailErrors").hasClass("hidden")){
           $("#emailErrors").addClass("hidden");
           $("#emailErrors").removeClass("error-message");
           $("#emailErrors").html("");
           $(".email-share .button").removeClass("sending");
       }
    }else{
        $("#emailErrors").html("No email addresses supplied.");
        $(".email-share .button").removeClass("sending");
        if ($("#emailErrors").hasClass("hidden")) {
            $("#emailErrors").removeClass("hidden");
            $(".email-share .button").removeClass("sending");
        }
        if (!$("#emailErrors").hasClass("error-message")) {
            $("#emailErrors").addClass("error-message");
            $(".email-share .button").removeClass("sending");
        }
        return false;
    }
    //post to server
    $.post(url,
        {
            emails: email_list
        }, function (data) {
            if(data.success == true){

                //clear out addresses & show message they were sent
                for(var i=0;i<num_children;i++) {
                    //validate emails
                    var box = $("#email_" + i)[0];
                    box.value = "";
                }
                $("#emailErrors").html("Invitations sent!");
                $(".email-share .button").removeClass("sending");
                $("#emailErrors").removeClass("hidden");
                if ($("#emailErrors").hasClass("error-message")) {
                     $("#emailErrors").removeClass("error-message");
                }
                if (!$("#emailErrors").hasClass("msgbox")) {
                    $("#emailErrors").addClass("msgbox");
                }
                
            }else{
                $("#emailErrors").html(data.errors);
                $(".email-share .button").removeClass("sending");
                if ($("#emailErrors").hasClass("hidden")) {

                    $("#emailErrors").removeClass("hidden");
                }
                if (!$("#emailErrors").hasClass("error-message")) {
                        $("#emailErrors").addClass("error-message");
                }
                return false;
            }
        },"json");


    return true;
}

function validateEmail(emailAddress){
    var pattern = /^([a-z\d!#$%&'*+\-\/=?^_`{|}~\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]+(\.[a-z\d!#$%&'*+\-\/=?^_`{|}~\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]+)*|"((([ \t]*\r\n)?[ \t]+)?([\x01-\x08\x0b\x0c\x0e-\x1f\x7f\x21\x23-\x5b\x5d-\x7e\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]|\\[\x01-\x09\x0b\x0c\x0d-\x7f\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]))*(([ \t]*\r\n)?[ \t]+)?")@(([a-z\d\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]|[a-z\d\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF][a-z\d\-._~\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]*[a-z\d\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])\.)+([a-z\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]|[a-z\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF][a-z\d\-._~\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]*[a-z\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])\.?$/i;
    return pattern.test(emailAddress);
}
