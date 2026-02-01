/**
 * LA Agenda Alerts - Site Scripts
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize FAQ Accordion
  initFaqAccordion();
  
  // Initialize Smooth Scroll
  initSmoothScroll();
  
  // Initialize Mobile Navigation
  initMobileNav();
});

/**
 * FAQ Accordion
 */
function initFaqAccordion() {
  const faqItems = document.querySelectorAll('.faq-item');
  
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    const answer = item.querySelector('.faq-answer');
    
    // Initially hide answers
    if (!item.hasAttribute('open')) {
      answer.style.display = 'none';
    }
    
    question.addEventListener('click', () => {
      const isOpen = item.hasAttribute('open');
      
      // Close all other items (optional - remove if you want multiple open)
      faqItems.forEach(otherItem => {
        if (otherItem !== item) {
          otherItem.removeAttribute('open');
          otherItem.querySelector('.faq-answer').style.display = 'none';
        }
      });
      
      // Toggle current item
      if (isOpen) {
        item.removeAttribute('open');
        answer.style.display = 'none';
      } else {
        item.setAttribute('open', '');
        answer.style.display = 'block';
      }
    });
    
    // Keyboard accessibility
    question.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        question.click();
      }
    });
  });
}

/**
 * Smooth Scroll for anchor links
 */
function initSmoothScroll() {
  const links = document.querySelectorAll('a[href^="#"]');
  
  links.forEach(link => {
    link.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href === '#') return;
      
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
        
        // Update URL without jumping
        history.pushState(null, '', href);
      }
    });
  });
  
  // Handle initial hash on page load
  if (window.location.hash) {
    const target = document.querySelector(window.location.hash);
    if (target) {
      setTimeout(() => {
        target.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  }
}

/**
 * Mobile Navigation Toggle
 */
function initMobileNav() {
  // Add mobile menu toggle if needed
  const nav = document.querySelector('.nav');
  const navLinks = document.querySelector('.nav-links');
  
  // Check if we need a mobile toggle
  if (window.innerWidth < 768 && navLinks) {
    // Mobile menu could be added here
    // For now, keeping it simple without hamburger
  }
}

/**
 * Get Free Alerts - Scroll to signup or open mailto
 */
function getFreeAlerts() {
  const signupSection = document.getElementById('signup');
  
  if (signupSection) {
    signupSection.scrollIntoView({ behavior: 'smooth' });
  } else {
    // Fallback to mailto
    const subject = encodeURIComponent('Sign up for LA Agenda Alerts');
    const body = encodeURIComponent(
      'Hi,\n\nI\'d like to sign up for LA Agenda Alerts.\n\n' +
      'Email: [your email]\n' +
      'Keywords I\'m interested in: [e.g., rent stabilization, zoning, CEQA]\n\n' +
      'Thanks!'
    );
    window.location.href = `mailto:contact@laagendaalerts.com?subject=${subject}&body=${body}`;
  }
}

/**
 * View Sources - Scroll to sources section
 */
function viewSources() {
  const sourcesSection = document.getElementById('sources');
  if (sourcesSection) {
    sourcesSection.scrollIntoView({ behavior: 'smooth' });
  }
}

/**
 * Start Free - Same as getFreeAlerts
 */
function startFree() {
  getFreeAlerts();
}

// Expose functions globally for onclick handlers
window.getFreeAlerts = getFreeAlerts;
window.viewSources = viewSources;
window.startFree = startFree;
