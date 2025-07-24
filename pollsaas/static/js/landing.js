// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Animate stats on scroll
const animateStats = () => {
    const stats = document.querySelectorAll('.stat-number');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = entry.target;
                const finalNumber = target.textContent;
                const isPercentage = finalNumber.includes('%');
                const numericValue = parseInt(finalNumber.replace(/[^\d]/g, ''));
                
                let current = 0;
                const increment = numericValue / 50;
                
                const timer = setInterval(() => {
                    current += increment;
                    if (current >= numericValue) {
                        current = numericValue;
                        clearInterval(timer);
                    }
                    
                    if (finalNumber.includes('K')) {
                        target.textContent = Math.floor(current / 1000) + 'K+';
                    } else if (finalNumber.includes('M')) {
                        target.textContent = (current / 1000000).toFixed(1) + 'M+';
                    } else if (isPercentage) {
                        target.textContent = current.toFixed(1) + '%';
                    } else {
                        target.textContent = Math.floor(current);
                    }
                }, 50);
                
                observer.unobserve(target);
            }
        });
    }, { threshold: 0.5 });
    
    stats.forEach(stat => observer.observe(stat));
};

// Initialize animations when DOM is loaded
document.addEventListener('DOMContentLoaded', animateStats);