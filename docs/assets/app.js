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
    openSignupMailto();
  }
}

/**
 * Open signup mailto
 */
function openSignupMailto() {
  const subject = encodeURIComponent('Sign up for LA Agenda Alerts');
  const body = encodeURIComponent(
    'Hi,\n\nI\'d like to sign up for LA Agenda Alerts.\n\n' +
    'Email: [your email]\n' +
    'Keywords I\'m interested in: [e.g., rent stabilization, zoning, CEQA, Hollywood, DTLA]\n\n' +
    'Thanks!'
  );
  window.location.href = `mailto:mnguyen9@usc.edu?subject=${subject}&body=${body}`;
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

/**
 * Open Payment Modal
 */
function openPaymentModal() {
  const modal = document.getElementById('paymentModal');
  if (modal) {
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }
}

/**
 * Close Payment Modal
 */
function closePaymentModal() {
  const modal = document.getElementById('paymentModal');
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

// Close modal on escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closePaymentModal();
  }
});

/**
 * Handle Signup Form Submission
 */
function handleSignup(event) {
  event.preventDefault();
  
  const email = document.getElementById('signupEmail').value;
  const name = document.getElementById('signupName').value;
  const customKeywords = document.getElementById('customKeywords').value;
  
  // Get checked keywords
  const checkedKeywords = Array.from(document.querySelectorAll('input[name="keywords"]:checked'))
    .map(cb => cb.value);
  
  // Combine all keywords
  const allKeywords = [...checkedKeywords];
  if (customKeywords) {
    allKeywords.push(...customKeywords.split(',').map(k => k.trim()).filter(k => k));
  }
  
  // Store signup data (in real app, this would go to your backend)
  const signupData = {
    email: email,
    name: name,
    keywords: allKeywords,
    timestamp: new Date().toISOString(),
    plan: 'free'
  };
  
  // Save to localStorage for demo purposes
  let signups = JSON.parse(localStorage.getItem('laagenda_signups') || '[]');
  signups.push(signupData);
  localStorage.setItem('laagenda_signups', JSON.stringify(signups));
  
  // Also prepare email data for you to process manually
  const emailBody = `NEW SIGNUP

Email: ${email}
Name: ${name || 'Not provided'}
Keywords: ${allKeywords.join(', ') || 'Default (all topics)'}
Plan: Free
Time: ${new Date().toLocaleString()}

---
To add this user to your system, forward this email to yourself and save to your subscriber database.`;
  
  // Open mailto with pre-filled data (for you to receive)
  const mailtoLink = `mailto:mnguyen9@usc.edu?subject=${encodeURIComponent('New LA Agenda Alerts Signup: ' + email)}&body=${encodeURIComponent(emailBody)}`;
  
  // Try to open mailto (may not work on all devices, that's ok)
  window.open(mailtoLink, '_blank');
  
  // Show success message
  document.getElementById('signupFormContainer').style.display = 'none';
  document.getElementById('signupSuccess').style.display = 'block';
  
  // Log for debugging
  console.log('Signup completed:', signupData);
}

/**
 * Reset Signup Form
 */
function resetSignup() {
  document.getElementById('signupForm').reset();
  document.getElementById('signupSuccess').style.display = 'none';
  document.getElementById('signupFormContainer').style.display = 'block';
}

// Expose functions globally for onclick handlers
window.getFreeAlerts = getFreeAlerts;
window.viewSources = viewSources;
window.startFree = startFree;
window.openPaymentModal = openPaymentModal;
window.closePaymentModal = closePaymentModal;
window.openSignupMailto = openSignupMailto;
window.handleSignup = handleSignup;
window.resetSignup = resetSignup;
