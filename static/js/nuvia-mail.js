document.addEventListener('DOMContentLoaded', () => {
  const steps = document.querySelectorAll('[data-setup-steps] .nuvia-mail-step');
  steps.forEach((step, index) => {
    const trigger = step.querySelector('[data-step-trigger]');
    if (!trigger) return;

    if (index === 0) {
      step.classList.add('is-open');
    }

    trigger.addEventListener('click', () => {
      step.classList.toggle('is-open');
    });
  });
});
