document.addEventListener('DOMContentLoaded', function() {
    // Animate title
    const title = document.querySelector('.animate-title');
    if (title) {
        const text = title.textContent;
        title.innerHTML = '';
        text.split('').forEach((char, index) => {
            const span = document.createElement('span');
            if (char === ' ') {
                span.innerHTML = '&nbsp;';
            } else {
                span.textContent = char;
            }
            span.style.animationDelay = `${index * 50}ms`;
            title.appendChild(span);
        });
    }

    // Scroll animations
    const animatedElements = document.querySelectorAll('.feature-card, .why-us-section .row, .roles-section .role-card');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, {
        threshold: 0.1
    });

    animatedElements.forEach((el, index) => {
        if (el.classList.contains('feature-card') || el.classList.contains('role-card')) {
            el.style.transitionDelay = `${(index % 4) * 100}ms`;
        }
        observer.observe(el);
    });

    // Interactive Tour
    const hotspots = document.querySelectorAll('.hotspot');
    const modals = document.querySelectorAll('.feature-modal');
    const closeModalButtons = document.querySelectorAll('.close-modal');

    hotspots.forEach(hotspot => {
        hotspot.addEventListener('click', () => {
            const feature = hotspot.dataset.feature;
            const modal = document.getElementById(`modal-${feature}`);
            if (modal) {
                modal.classList.add('visible');
            }
        });
    });

    closeModalButtons.forEach(button => {
        button.addEventListener('click', () => {
            button.closest('.feature-modal').classList.remove('visible');
        });
    });

    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('visible');
            }
        });
    });
});
