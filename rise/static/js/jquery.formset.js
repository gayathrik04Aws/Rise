(function($){

    function initializeTemplate($template, count, prefix) {
        var template = $template.clone();
        template.find('label').each(function(idx, label){
            $label = $(label);
            $label.attr('for', $label.attr('for').replace(prefix, count));
        });
        template.find('input, select, textarea').each(function(idx, field){
            $field = $(field);
            if($field.attr('id')) {
                $field.attr('id', $field.attr('id').replace(prefix, count));
            }
            if($field.attr('name')) {
                $field.attr('name', $field.attr('name').replace(prefix, count));
            }
        });
        return template;
    }

    $.fn.formset = function(options) {
        if(!options) {
            options = {};
        }

        var itemClass = options.itemClass || 'form-item';
        var addItemClass = options.addItemClass || 'add-new';
        var buttonTemplate = options.buttonTemplate;
        var callback = options.callback || function(){};

        this.each(function() {
            var $formset = $(this);
            var prefix = $formset.attr('data-prefix');
            var $total = $formset.find('[name=' + prefix + '-TOTAL_FORMS]');
            var $template = $formset.find('.' + itemClass).last().detach();
            var max = Number($formset.find('[name=' + prefix + '-MAX_NUM_FORMS]').val());
            var initial = Number($formset.find('[name=' + prefix + '-INITIAL_FORMS]').val());

            buttonElement = '';
            if (buttonTemplate) {
                buttonElement = $(buttonTemplate);
                console.log('button element: ' + buttonElement);
                $formset.append(buttonElement);
            }

            $formset.on('click', '.' + addItemClass, function(e){
                e.preventDefault();

                var count = Number($total.val());
                if (count >= max) {
                    return false;
                }
                var formItem = initializeTemplate($template, count, initial);
                var lastItem = $formset.find('.' + itemClass).last();
                if (lastItem.length) {
                    lastItem.after(formItem);
                } else if (buttonElement){
                    buttonElement.before(formItem);
                } else {
                    $formset.append(formItem);
                }

                $total.val(count + 1);
                callback($formset, formItem);
            });

            $formset.on('click', "[name$=DELETE]", function(e){
                $(e.target).closest('.' + itemClass).hide();
            });
        });
    };
})( jQuery );
