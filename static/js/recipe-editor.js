/**
 * Inicjalizacja edytora WYSIWYG dla formularza przepisu
 */
document.addEventListener('DOMContentLoaded', function() {
    // Znajdź pola formularza do opisu i instrukcji
    const descriptionField = document.querySelector('#id_description');
    const instructionsField = document.querySelector('#id_instructions');
    
    // Inicjalizacja edytora tylko jeśli pola istnieją na stronie
    if (descriptionField) {
        initializeEditor(descriptionField);
    }
    
    if (instructionsField) {
        initializeEditor(instructionsField);
    }
    
    // Inicjalizacja edytora TinyMCE
    function initializeEditor(element) {
        // Zapisz oryginalny element formularza
        const originalElement = element;
        const elementId = element.id;
        
        // Upewnij się, że TinyMCE jest załadowany
        if (typeof tinymce !== 'undefined') {
            tinymce.init({
                selector: `#${elementId}`,
                height: 300,
                menubar: false,
                plugins: [
                    'advlist autolink lists link image charmap print preview anchor',
                    'searchreplace visualblocks code fullscreen',
                    'insertdatetime media table paste code help wordcount'
                ],
                toolbar: 'undo redo | formatselect | ' +
                'bold italic backcolor | alignleft aligncenter ' +
                'alignright alignjustify | bullist numlist outdent indent | ' +
                'removeformat | help',
                content_style: 'body { font-family:Helvetica,Arial,sans-serif; font-size:14px }',
                setup: function (editor) {
                    // Synchronizuj zawartość edytora z oryginalnym polem formularza
                    editor.on('change', function () {
                        editor.save(); // Zapisz zawartość do oryginalnego textarea
                    });
                }
            });
        } else {
            console.error('TinyMCE nie jest dostępny. Upewnij się, że biblioteka została załadowana.');
        }
    }
}); 