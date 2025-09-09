document.addEventListener('DOMContentLoaded', function() {
    // Máscara para campos de patrimônio
    const patrimonyInputs = document.querySelectorAll('.patrimony');
    patrimonyInputs.forEach(input => {
        input.addEventListener('input', function() {
            this.value = this.value.replace(/\D/g, '').slice(0, 8);
        });
    });

    // Converter para maiúsculas - REFORÇADO
    const uppercaseInputs = document.querySelectorAll('.uppercase');
    uppercaseInputs.forEach(input => {
        // Evento input
        input.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });

        // Evento blur (quando sai do campo)
        input.addEventListener('blur', function() {
            this.value = this.value.toUpperCase();
        });

        // Evento change
        input.addEventListener('change', function() {
            this.value = this.value.toUpperCase();
        });
    });

    // Máscara para MASP (8 dígitos)
    const maspInputs = document.querySelectorAll('.masp');
    maspInputs.forEach(input => {
        input.addEventListener('input', function() {
            this.value = this.value.replace(/\D/g, '').slice(0, 8);
        });
    });

    // Fechar alertas automaticamente após 5 segundos
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Validação de confirmação de senha
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const password = this.querySelector('input[name="password"]');
            const confirmPassword = this.querySelector('input[name="confirm_password"]');
            const newPassword = this.querySelector('input[name="new_password"]');
            const confirmNewPassword = this.querySelector('input[name="confirm_password"]');

            if (password && confirmPassword && password.value !== confirmPassword.value) {
                e.preventDefault();
                alert('As senhas não coincidem!');
                confirmPassword.focus();
            }

            if (newPassword && confirmNewPassword && newPassword.value && newPassword.value !== confirmNewPassword.value) {
                e.preventDefault();
                alert('As novas senhas não coincidem!');
                confirmNewPassword.focus();
            }

            // Garantir caixa alta antes do envio
            const uppercaseFields = this.querySelectorAll('.uppercase');
            uppercaseFields.forEach(field => {
                field.value = field.value.toUpperCase();
            });
        });
    });
});