$(function() {
    $('#cc-number').payment('formatCardNumber');
    $('#cc-month, #cc-year').payment('restrictNumeric');
    $('#routing-number, #account-number').payment('restrictNumeric');
    $('#ccv').payment('formatCardCVC');

    $('#bank-form').submit(function(event) {
        var $form = $(this);

        $form.find('.error-message').remove();
        $('input.error').removeClass('error');

        // Disable the submit button to prevent repeated clicks
        $form.find('button').prop('disabled', true);

        Stripe.bankAccount.createToken($form, stripeResponseHandler);

        return false;
    });

    $('#register-payment-form').submit(function(event) {
        var $form;
        if ($('input[value=new]').is(':checked')) {
            $form = $(this);
            $form.find('.error-message').remove();
            $('input.error').removeClass('error');

            // Disable the submit button to prevent repeated clicks
            $form.find('button').prop('disabled', true);

            var client = new braintree.api.Client({clientToken: BRAINTREE_CLIENT_TOKEN});

            client.tokenizeCard({
                    number: $('#cc-number').val(),
                    expirationMonth: $('#cc-month').val(),
                    expirationYear: $('#cc-year').val(),
                    cvv: $('#ccv').val(),
                },
                function (err, nonce) {
                    $form.append($('<input type="hidden" name="payment_method_nonce" />').val(nonce));
                    $form.get(0).submit();
                }
            );

            // Prevent the form from submitting with the default action
            return false;
        } else if ($('input[value=ach]').is(':checked')) {
            $form = $(this);
            $form.find('.error-message').remove();
            $('input.error').removeClass('error');

            // Disable the submit button to prevent repeated clicks
            $form.find('button').prop('disabled', true);

            Stripe.bankAccount.createToken($form, stripeResponseHandler);

            return false;
        } else {
            return true;
        }

    });


    $('#signup-payment-form').submit(function(event) {
        var $form;
        if ($('input[value=Card]').is(':checked')) {
            $form = $(this);
            $form.find('.error-message').remove();
            $('input.error').removeClass('error');

            // Disable the submit button to prevent repeated clicks
            $form.find('button').prop('disabled', true);

            var client = new braintree.api.Client({clientToken: BRAINTREE_CLIENT_TOKEN});

            client.tokenizeCard({
                    number: $('#cc-number').val(),
                    expirationMonth: $('#cc-month').val(),
                    expirationYear: $('#cc-year').val(),
                    cvv: $('#ccv').val(),
                },
                function (err, nonce) {
                    $('input[name=token]').remove();
                    $form.append($('<input type="hidden" name="token" />').val(nonce));
                    $('#credit_card_payment_modal').show();
                    // $form.get(0).submit();
                }
            );

            // Prevent the form from submitting with the default action
            return false;
        } else if ($('input[value=ACH]').is(':checked')) {
            $form = $(this);
            $form.find('.error-message').remove();
            $('input.error').removeClass('error');

            // Disable the submit button to prevent repeated clicks
            $form.find('button').prop('disabled', true);

            Stripe.bankAccount.createToken($form, stripeResponseHandler);

            return false;
        } else {
            return true;
        }

    });


    $('#signup-anywhere-payment-form').submit(function(event) {
        var $form;
        if ($('input[value=Card]').is(':checked')) {
            $form = $(this);
            $form.find('.error-message').remove();
            $('input.error').removeClass('error');

            // Disable the submit button to prevent repeated clicks
            $form.find('button').prop('disabled', true);

            var client = new braintree.api.Client({clientToken: BRAINTREE_CLIENT_TOKEN});

            client.tokenizeCard({
                    number: $('#cc-number').val(),
                    expirationMonth: $('#cc-month').val(),
                    expirationYear: $('#cc-year').val(),
                    cvv: $('#ccv').val(),
                },
                function (err, nonce) {
                    $('input[name=token]').remove();
                    $form.append($('<input type="hidden" name="token" />').val(nonce));
                    //no modal here since we are not charging.
                    //$('#credit_card_payment_modal').show();
                    $form.get(0).submit();
                }
            );

            return false;
        } else if ($('input[value=ACH]').is(':checked')) {
            $form = $(this);
            $form.find('.error-message').remove();
            $('input.error').removeClass('error');

            // Disable the submit button to prevent repeated clicks
            $form.find('button').prop('disabled', true);

            Stripe.bankAccount.createToken($form, stripeResponseHandler);

            return false;
        } else {
            return true;
        }

    });


    $('#submit_ach_verification').on(clickAction, function(event) {
        if ($('#ach_deposit_modal').length > 0) {
            event.preventDefault();
            $('#ach_deposit_modal').show();
            return false;
        }
    });

    $('#confirm_credit_card_payment').on(clickAction, function(event) {
        event.preventDefault();
        $(this).remove();
        $('#signup-payment-form').get(0).submit();
    });

    $('#confirm_ach_payment').on(clickAction, function(event) {
        event.preventDefault();
        $(this).remove();
        $('#signup-payment-form').get(0).submit();
    });

    $('#confirm_ach_deposit').on(clickAction, function(event) {
        event.preventDefault();
        $('#ach_payment_modal').remove();
        $('#payment-form').get(0).submit();
    });

    $('#confirm_credit_deposit').on(clickAction, function(event) {
        event.preventDefault();
        $('#credit_deposit_modal').remove();
        $('#credit_card_form').submit();
    });

    $('#credit_card_form').submit(function(event) {
        var $form = $(this);
        if ($('input[name="payment_method_nonce"]').length > 0) {
            return true;
        }
        else{
            $form.find('.error-message').remove();
            $('input.error').removeClass('error');

            // Disable the submit button to prevent repeated clicks
            $form.find('button').prop('disabled', true);

            var client = new braintree.api.Client({clientToken: BRAINTREE_CLIENT_TOKEN});

            client.tokenizeCard({
                    number: $('#cc-number').val(),
                    expirationMonth: $('#cc-month').val(),
                    expirationYear: $('#cc-year').val(),
                    cvv: $('#ccv').val(),
                },
                function (err, nonce) {
                    $('input[name="payment_method_nonce"]').remove();
                    $form.append($('<input type="hidden" name="payment_method_nonce" />').val(nonce));
                    if ($('#credit_deposit_modal').length){
                        $('#credit_deposit_modal').show();
                    }
                    else{
                        $form.submit();
                    }
                }
            );

            // Prevent the form from submitting with the default action
            return false;
        }
    });

    $('#flight-payment-form').submit(function(event) {
        if ($('#cc-number').val()) {
            if ($('input[name="payment_method_nonce"]').length > 0) {
                return true;
            }else {
                var client = new braintree.api.Client({clientToken: BRAINTREE_CLIENT_TOKEN});
                var $form = $(this);
                client.tokenizeCard({
                            number: $('#cc-number').val(),
                            expirationMonth: $('#cc-month').val(),
                            expirationYear: $('#cc-year').val(),
                            cvv: $('#ccv').val(),
                        },
                        function (err, nonce) {
                            $('input[name=payment_method_nonce]').remove();
                            $form.append($('<input type="hidden" name="payment_method_nonce" />').val(nonce));
                            $form.submit();
                        }
                );
                return false;
            }
        }


    });

    // register_payment.html
    toggleNewPaymentForm();
    toggleManualPaymentForm();
    toggleAchPaymentForm();
    // payment.html and corporate_payment.html
    toggleCreditCardFieldset();
    toggleBankAccountFieldset();
    toggleManualFieldset();

    $('.payment-choice input:radio').change(function() {
        toggleNewPaymentForm();
        toggleManualPaymentForm();
        toggleAchPaymentForm();
    });

    $('#payment-info-section input:radio').change(function() {
        toggleCreditCardFieldset();
        toggleBankAccountFieldset();
        toggleManualFieldset();
    });
});

function toggleNewPaymentForm() {
    var target = '#payment-choice-new';

    if ($(target).is(':checked')) {
        $('#billing_address').appendTo('#new_payment_form').show();
        $('#new_payment_form').show();
    } else {
        $('#new_payment_form, #billing_address').hide();
    }
}

function toggleManualPaymentForm() {
    var target = '#payment-choice-manual';

    if($(target).is(':checked')) {
        $('.manual-alert').show();
    } else {
        $('.manual-alert').hide();
    }
}

function toggleAchPaymentForm() {
    var target = '#payment-choice-ach';

    if ($(target).is(':checked')) {
        $('#billing_address').appendTo('#ach_payment_form').show();
        $('#ach_payment_form').show();
    } else {
        $('#ach_payment_form').hide();
    }
}


function toggleCreditCardFieldset() {
    var target = '#id_payment_method_1';

    if($(target).is(':checked')) {
        $('fieldset#credit-card').show();
    } else {
        $('fieldset#credit-card').hide();
    }
}

function toggleBankAccountFieldset() {
    var target = '#id_payment_method_0';

    if($(target).is(':checked')) {
        $('fieldset#bank-account').show();
    } else {
        $('fieldset#bank-account').hide();
    }
}

function toggleManualFieldset() {
    var target = '#id_payment_method_2';

    if($(target).is(':checked')) {
        $('#manual-account').show();
    } else {
        $('#manual-account').hide();
    }
}


////
//// Shipping address checkbox
function showShippingAddressForm() {
    var target = '#same-as-billing';

    if($(target).is(':checked')) {
        $('#shipping-info-fieldset').hide();
    } else {
        $('#shipping-info-fieldset').show();
    }
}


$(document).ready(function(){
    $('#same-as-billing').change(function(){
      showShippingAddressForm();
    });
});

function stripeResponseHandler(status, response) {
    var $form = $('#payment-form, #bank-form, #register-payment-form, #flight-payment-form, #signup-payment-form,  #signup-anywhere-payment-form');

    if (response.error) {
        // Show the errors on the form
        $form.prepend($('<div class="error-message"></div>').html(response.error.message));
        $form.find('button').prop('disabled', false);

        if (response.error.param === 'exp_year') {
            $('#cc-year').addClass('error');
        } else if (response.error.param === 'exp_month') {
            $('#cc-month').addClass('error');
        } else if (response.error.param === 'cvc') {
            $('#ccv').addClass('error');
        } else if (response.error.param === 'number') {
            $('#cc-number').addClass('error');
        }
    } else {
        // response contains id and card, which contains additional card details
        var token = response.id;
        var routing = response.bank_account.routing_number;
        var last4 = response.bank_account.last4;
        // Insert the token into the form so it gets submitted to the server
        $form.append($('<input type="hidden" name="token" />').val(token));
        $form.append($('<input type="hidden" name="routing" />').val(routing));
        $form.append($('<input type="hidden" name="last4" />').val(last4));
        // and submit
        if ($('#ach_payment_modal').length > 0) {
            $('#ach_payment_modal').show();
        } else {
            $form.get(0).submit();
        }

    }
}
