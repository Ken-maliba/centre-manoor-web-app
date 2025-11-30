document.addEventListener('DOMContentLoaded', function() {
    
    // ====================================================
    // Éléments de la page (Navigation & Contenu)
    // ====================================================
    const sections = document.querySelectorAll('.content-section');
    const mainTitle = document.getElementById('main-title');
    
    // Liens de Navigation (IDs des liens dans le <nav>)
    const navPreInscription = document.getElementById('navPreInscription');
    const homeAnchor = document.getElementById('home-anchor'); 
    const navAccueil = document.getElementById('navAccueil');
    const navToggleSommaire = document.getElementById('toggleSommaire'); 
    const navToggleContact = document.getElementById('navToggleContact');
    
    const menuToggle = document.querySelector('.menu-toggle');
    const navMenu = document.getElementById('nav-menu');
    
    // Référence à la galerie et au formulaire
    const gallerySection = document.getElementById('gallery-section');
    const inscriptionForm = document.querySelector('.form-grid'); // Utilisation de la classe car il n'y a pas d'ID
    const telephoneInput = document.getElementById('telephone');


    // ====================================================
    // I. LOGIQUE DE LA NAVIGATION & GESTION DES SECTIONS
    // (Transféré depuis le bas de index.html)
    // ====================================================

    // LOGIQUE DE LA NAVIGATION MOBILE
    if (menuToggle && navMenu) {
        menuToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
        
        // Ferme le menu après avoir cliqué sur un lien (utile sur mobile)
        navMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    navMenu.classList.remove('active');
                }
            });
        });
    }

    function showSection(sectionId, titleText) {
        // 1. Masquer toutes les sections de contenu
        sections.forEach(section => {
            section.style.display = 'none';
        });
        
        // Masquer la galerie
        gallerySection.style.display = 'none';

        // 2. Afficher l'ancre pour centrer le titre
        homeAnchor.style.display = 'flex'; 

        // 3. Afficher la section demandée
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
            targetSection.style.display = 'block';
            
            // 4. Mettre à jour et afficher le titre principal
            mainTitle.textContent = titleText;
            mainTitle.style.display = 'block';

            // 5. Défilement vers l'ancre de la page 
            homeAnchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    
    // --- GESTION DES CLICS ---

    // 1. LIEN INSCRIPTION
    if (navPreInscription) {
        navPreInscription.addEventListener('click', function(e) {
            e.preventDefault();
            showSection('formulaire-content', 'Formulaire de Pré-Inscription');
        });
    }

    // 2. SOMMAIRE
    if (navToggleSommaire) {
        navToggleSommaire.addEventListener('click', function(e) {
            e.preventDefault();
            showSection('sommaire-content', 'Sommaire de Présentation');
        });
    }

    // 3. CONTACT
    if (navToggleContact) {
        navToggleContact.addEventListener('click', function(e) {
            e.preventDefault();
            showSection('contact', 'Coordonnées du Centre');
        });
    }
    
    // 4. ACCUEIL
    if (navAccueil) {
        navAccueil.addEventListener('click', function(e) {
            e.preventDefault(); 
            
            sections.forEach(section => { section.style.display = 'none'; });
            mainTitle.style.display = 'none';
            homeAnchor.style.display = 'flex'; 

            // Afficher la galerie
            gallerySection.style.display = 'block'; 

            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // ====================================================
    // II. LOGIQUE DU MODAL / LIGHTBOX
    // (Transféré depuis le bas de index.html)
    // ====================================================
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const modalCaption = document.getElementById('modalCaption');
    const closeModal = document.getElementById('closeModal');
    const photoCards = document.querySelectorAll('.photo-card'); 

    // 1. Gérer l'ouverture du modal au clic sur une carte
    photoCards.forEach(card => {
        card.addEventListener('click', function() {
            const imgSrc = this.getAttribute('data-src');
            const imgCaption = this.getAttribute('data-caption');
            
            if (modal && modalImage) {
                modal.style.display = 'flex';
                modalImage.src = imgSrc;
                modalCaption.textContent = imgCaption;
                document.body.style.overflow = 'hidden'; 
            }
        });
    });

    // 2. Gérer la fermeture au clic sur le 'X'
    if (closeModal) {
        closeModal.addEventListener('click', function() {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto'; 
        });
    }

    // 3. Gérer la fermeture au clic en dehors de l'image
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto'; 
        }
    });
    
    // 4. Gérer la fermeture avec la touche ECHAP
    document.addEventListener('keydown', function(event) {
        if (event.key === "Escape" && modal && modal.style.display === 'flex') {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto'; 
        }
    });

    // ====================================================
    // III. VALIDATION DU FORMULAIRE D'INSCRIPTION
    // (Logique conservée de votre script initial)
    // ====================================================

    if (inscriptionForm && telephoneInput) {
        inscriptionForm.addEventListener('submit', function(e) {
            
            // Validation du numéro de téléphone (Mali : 8 chiffres)
            const telephoneValue = telephoneInput.value.replace(/[^0-9]/g, ''); 
            
            if (telephoneValue.length !== 8) {
                e.preventDefault(); // Empêche l'envoi du formulaire
                
                // Alert et focus pour corriger
                alert('Erreur de validation : Le numéro de téléphone doit être composé de 8 chiffres (Mali). Veuillez corriger.');
                telephoneInput.focus();
                return;
            }
            
            // Le formulaire sera envoyé au serveur Flask.
        });
    }
});
