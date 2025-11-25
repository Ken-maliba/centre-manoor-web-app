document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.querySelector('.menu-toggle');
    const navMenu = document.getElementById('nav-menu');
    const inscriptionForm = document.getElementById('inscriptionForm');
    const telephoneInput = document.getElementById('telephone');

    // --- 1. Gestion du Menu Mobile (Hamburger) ---
    if (menuToggle && navMenu) {
        menuToggle.addEventListener('click', function() {
            // Bascule la classe 'active' pour afficher/cacher le menu
            navMenu.classList.toggle('active');
        });

        // Ferme le menu après avoir cliqué sur un lien (utile sur mobile)
        const navLinks = navMenu.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (navMenu.classList.contains('active')) {
                    navMenu.classList.remove('active');
                }
            });
        });
    }

    // --- 2. Validation du Formulaire d'Inscription ---
    if (inscriptionForm) {
        inscriptionForm.addEventListener('submit', function(e) {
            
            // Validation du numéro de téléphone (Mali : 8 chiffres)
            // Nettoie la valeur (garde que les chiffres)
            const telephoneValue = telephoneInput.value.replace(/[^0-9]/g, ''); 
            
            if (telephoneValue.length !== 8) {
                e.preventDefault(); // Empêche l'envoi du formulaire
                
                // Alert et focus pour corriger
                alert('Erreur de validation : Le numéro de téléphone doit être composé de 8 chiffres (Mali). Veuillez corriger.');
                telephoneInput.focus();
                return;
            }
            
            // Si la validation passe, le formulaire sera envoyé au serveur Flask.
            // On retire le e.preventDefault() ici pour permettre l'envoi au backend.
            // Le serveur Flask (app.py) prend le relais après cette étape.
        });
    }
});