// Loading Animation
window.addEventListener('load', () => {
    const loader = document.querySelector('.loading');
    if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => {
            loader.style.display = 'none';
        }, 500);
    }
});

// Custom Cursor
const cursor = document.querySelector('.cursor');

document.addEventListener('mousemove', (e) => {
    requestAnimationFrame(() => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    });
});

// Service item background color change
const serviceItems = document.querySelectorAll('.service-item');
serviceItems.forEach(item => {
    item.addEventListener('mouseenter', () => {
        const color = item.getAttribute('data-color');
        document.body.style.backgroundColor = color;
    });

    item.addEventListener('mouseleave', () => {
        document.body.style.backgroundColor = 'var(--bg-color)';
    });
});

// Text reveal animation
const textElements = document.querySelectorAll('.text-reveal');
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animation = 'revealText 1s ease forwards';
        }
    });
}, {
    threshold: 0.1
});

textElements.forEach(element => {
    observer.observe(element);
});

// Circular button rotation
const circularButtons = document.querySelectorAll('.btn-circle');
circularButtons.forEach(button => {
    button.addEventListener('mousemove', (e) => {
        const rect = button.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        const angle = Math.atan2(y, x) * (180 / Math.PI);
        
        const arrow = button.querySelector('.arrow');
        if (arrow) {
            arrow.style.transform = `rotate(${angle}deg)`;
        }
    });

    button.addEventListener('mouseleave', () => {
        const arrow = button.querySelector('.arrow');
        if (arrow) {
            arrow.style.transform = 'rotate(0deg)';
        }
    });
});

// Form interaction
const formGroups = document.querySelectorAll('.form-group');
formGroups.forEach(group => {
    const input = group.querySelector('input, textarea');
    const line = group.querySelector('.line');

    if (input && line) {
        input.addEventListener('focus', () => {
            line.style.transform = 'scaleX(1)';
            line.style.transformOrigin = 'left';
        });

        input.addEventListener('blur', () => {
            if (!input.value) {
                line.style.transform = 'scaleX(0)';
            }
        });
    }
}); 