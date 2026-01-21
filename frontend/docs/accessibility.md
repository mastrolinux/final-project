# Accessibility Guidelines

This document defines accessibility requirements and implementation guidelines for the Identity Management frontend application. The application targets WCAG 2.1 Level AA compliance.

## WCAG 2.1 AA Compliance Checklist

### Perceivable

#### 1.1 Text Alternatives

- [ ] All images have meaningful `alt` text
- [ ] Decorative images have `alt=""`
- [ ] Icons have accessible labels (via `aria-label` or visually hidden text)
- [ ] Complex images have long descriptions

#### 1.2 Time-based Media

- [ ] Audio content has text transcripts
- [ ] Video content has captions
- [ ] Audio descriptions for video (if applicable)

#### 1.3 Adaptable

- [ ] Content structure uses semantic HTML
- [ ] Reading order is logical
- [ ] Instructions don't rely solely on sensory characteristics
- [ ] Content works in both portrait and landscape orientations

#### 1.4 Distinguishable

- [ ] Color is not the only means of conveying information
- [ ] Text contrast ratio is at least 4.5:1 (3:1 for large text)
- [ ] Text can be resized up to 200% without loss of functionality
- [ ] Images of text are avoided (except logos)
- [ ] Content reflows at 320px width
- [ ] Non-text contrast is at least 3:1
- [ ] Text spacing can be adjusted without loss of content
- [ ] Content on hover/focus is dismissible, hoverable, and persistent

### Operable

#### 2.1 Keyboard Accessible

- [ ] All functionality is available via keyboard
- [ ] No keyboard traps
- [ ] Keyboard shortcuts can be disabled or remapped

#### 2.2 Enough Time

- [ ] Timing can be adjusted or disabled
- [ ] Auto-updating content can be paused, stopped, or hidden
- [ ] No time limits on authentication (or extendable)

#### 2.3 Seizures and Physical Reactions

- [ ] No content flashes more than 3 times per second

#### 2.4 Navigable

- [ ] Skip links are provided
- [ ] Pages have descriptive titles
- [ ] Focus order is logical
- [ ] Link purpose is clear from text
- [ ] Multiple ways to find pages
- [ ] Headings and labels are descriptive
- [ ] Focus is visible

#### 2.5 Input Modalities

- [ ] Touch targets are at least 44x44px
- [ ] Motion-based actions have alternatives
- [ ] Pointer gestures have single-pointer alternatives

### Understandable

#### 3.1 Readable

- [ ] Page language is identified (`lang` attribute)
- [ ] Language changes are marked

#### 3.2 Predictable

- [ ] Focus doesn't trigger unexpected changes
- [ ] Input doesn't trigger unexpected changes
- [ ] Navigation is consistent
- [ ] Components are identified consistently

#### 3.3 Input Assistance

- [ ] Errors are identified and described
- [ ] Labels or instructions are provided
- [ ] Error suggestions are offered
- [ ] Error prevention for legal/financial data

### Robust

#### 4.1 Compatible

- [ ] HTML is valid
- [ ] Name, role, value are programmatically determined
- [ ] Status messages are announced to screen readers

---

## Color Contrast Requirements

### Text Contrast

| Element | Minimum Ratio | Requirement |
|---------|---------------|-------------|
| Body text | 4.5:1 | AA |
| Large text (18px+ or 14px bold) | 3:1 | AA |
| Placeholder text | 4.5:1 | AA |
| Disabled text | No requirement | - |

### Non-Text Contrast

| Element | Minimum Ratio | Requirement |
|---------|---------------|-------------|
| UI components (buttons, inputs) | 3:1 | AA |
| Focus indicators | 3:1 | AA |
| Icons (meaningful) | 3:1 | AA |
| Graphical objects | 3:1 | AA |

### Color Palette Compliance

The design system colors in `variables.css` have been selected to meet contrast requirements:

| Combination | Ratio | Status |
|-------------|-------|--------|
| Primary text on white | 12.6:1 | Pass |
| Secondary text on white | 4.5:1 | Pass |
| Primary button text on primary | 4.6:1 | Pass |
| Error text on white | 4.5:1 | Pass |
| Success text on white | 4.5:1 | Pass |
| Warning text on white | 4.5:1 | Pass |

### Testing Tools

- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- Browser DevTools accessibility panel
- axe DevTools extension

---

## Keyboard Navigation

### Focus Management

#### Focus Visibility

All interactive elements must have a visible focus indicator:

```css
:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

/* Remove default outline but keep for keyboard users */
:focus:not(:focus-visible) {
  outline: none;
}
```

#### Focus Order

Focus order must follow a logical reading order:

1. Skip link (first focusable element)
2. Header navigation
3. Main content (top to bottom, left to right)
4. Footer navigation

#### Focus Trapping

Modals must trap focus within the dialog:

```typescript
// Example focus trap implementation
function trapFocus(element: HTMLElement) {
  const focusableElements = element.querySelectorAll(
    'a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])'
  )
  const firstElement = focusableElements[0] as HTMLElement
  const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement

  element.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault()
        lastElement.focus()
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault()
        firstElement.focus()
      }
    }
  })
}
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Tab | Move focus forward |
| Shift + Tab | Move focus backward |
| Enter | Activate button/link |
| Space | Toggle checkbox, activate button |
| Escape | Close modal/dropdown |
| Arrow keys | Navigate within components |

### Skip Links

Provide skip links for main content areas:

```html
<a href="#main-content" class="skip-link">
  Skip to main content
</a>

<main id="main-content" tabindex="-1">
  <!-- Main content -->
</main>
```

```css
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--bg-secondary);
  padding: var(--spacing-2) var(--spacing-4);
  z-index: var(--z-tooltip);
}

.skip-link:focus {
  top: 0;
}
```

---

## ARIA Labels and Roles

### Landmark Roles

Use semantic HTML elements that provide implicit roles:

| HTML Element | ARIA Role |
|--------------|-----------|
| `<header>` | banner |
| `<nav>` | navigation |
| `<main>` | main |
| `<aside>` | complementary |
| `<footer>` | contentinfo |
| `<section>` | region (with aria-label) |

### Common ARIA Patterns

#### Buttons

```html
<!-- Standard button -->
<button type="button">Save</button>

<!-- Icon button -->
<button type="button" aria-label="Close dialog">
  <XIcon aria-hidden="true" />
</button>

<!-- Toggle button -->
<button type="button" aria-pressed="false">
  Dark mode
</button>

<!-- Loading button -->
<button type="button" disabled aria-busy="true">
  <Spinner aria-hidden="true" />
  Saving...
</button>
```

#### Forms

```html
<!-- Required field -->
<label for="email">
  Email <span aria-hidden="true">*</span>
</label>
<input 
  type="email" 
  id="email" 
  aria-required="true"
  aria-describedby="email-hint"
>
<p id="email-hint">We'll send a verification link to this address.</p>

<!-- Field with error -->
<input 
  type="email" 
  id="email" 
  aria-invalid="true"
  aria-describedby="email-error"
>
<p id="email-error" role="alert">Please enter a valid email address.</p>
```

#### Dialogs

```html
<div 
  role="dialog" 
  aria-modal="true" 
  aria-labelledby="dialog-title"
  aria-describedby="dialog-description"
>
  <h2 id="dialog-title">Confirm Action</h2>
  <p id="dialog-description">Are you sure you want to delete this context?</p>
  <button type="button">Cancel</button>
  <button type="button">Delete</button>
</div>
```

#### Alerts and Notifications

```html
<!-- Static alert -->
<div role="alert">
  Your session will expire in 5 minutes.
</div>

<!-- Live region for dynamic content -->
<div aria-live="polite" aria-atomic="true">
  <!-- Content updates announced to screen readers -->
</div>

<!-- Toast notification -->
<div role="status" aria-live="polite">
  Profile saved successfully.
</div>
```

#### Navigation

```html
<nav aria-label="Main navigation">
  <ul role="menubar">
    <li role="none">
      <a href="/" role="menuitem">Home</a>
    </li>
    <li role="none">
      <a href="/profile" role="menuitem" aria-current="page">Profile</a>
    </li>
  </ul>
</nav>
```

#### Tabs

```html
<div role="tablist" aria-label="Profile sections">
  <button 
    role="tab" 
    aria-selected="true" 
    aria-controls="panel-basic"
    id="tab-basic"
  >
    Basic Info
  </button>
  <button 
    role="tab" 
    aria-selected="false" 
    aria-controls="panel-contexts"
    id="tab-contexts"
    tabindex="-1"
  >
    Contexts
  </button>
</div>

<div 
  role="tabpanel" 
  id="panel-basic" 
  aria-labelledby="tab-basic"
  tabindex="0"
>
  <!-- Tab content -->
</div>
```

---

## Screen Reader Considerations

### Visually Hidden Text

Use visually hidden text to provide context for screen readers:

```css
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

```html
<button type="button">
  <TrashIcon aria-hidden="true" />
  <span class="visually-hidden">Delete context: Professional</span>
</button>
```

### Announcing Dynamic Content

Use ARIA live regions for content that updates dynamically:

```html
<!-- Polite: Wait for user to finish current task -->
<div aria-live="polite">
  <!-- Search results, form validation -->
</div>

<!-- Assertive: Interrupt immediately -->
<div aria-live="assertive">
  <!-- Critical errors, session timeout warnings -->
</div>
```

### Content Structure

Use proper heading hierarchy:

```html
<h1>Profile Settings</h1>
  <h2>Basic Information</h2>
    <h3>Name</h3>
    <h3>Contact</h3>
  <h2>Identity Contexts</h2>
    <h3>Professional</h3>
    <h3>Social</h3>
```

### Tables

Make data tables accessible:

```html
<table>
  <caption>Your identity contexts</caption>
  <thead>
    <tr>
      <th scope="col">Context</th>
      <th scope="col">Type</th>
      <th scope="col">Status</th>
      <th scope="col">Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">Work Profile</th>
      <td>Professional</td>
      <td>Active</td>
      <td>
        <button aria-label="Edit Work Profile">Edit</button>
      </td>
    </tr>
  </tbody>
</table>
```

---

## Focus Management Strategy

### Page Navigation

When navigating between pages:

1. Move focus to the main content area
2. Announce the new page title
3. Update the document title

```typescript
// In router navigation guard
router.afterEach((to) => {
  // Update document title
  document.title = to.meta.title 
    ? `${to.meta.title} | Identity Management` 
    : 'Identity Management'
  
  // Move focus to main content
  nextTick(() => {
    const main = document.querySelector('main')
    if (main) {
      main.setAttribute('tabindex', '-1')
      main.focus()
      main.removeAttribute('tabindex')
    }
  })
})
```

### Modal Dialogs

When opening a modal:

1. Store the previously focused element
2. Move focus to the modal (or first focusable element)
3. Trap focus within the modal
4. On close, restore focus to the trigger element

```typescript
// Example modal focus management
const previouslyFocused = ref<HTMLElement | null>(null)

function openModal() {
  previouslyFocused.value = document.activeElement as HTMLElement
  isOpen.value = true
  nextTick(() => {
    modalRef.value?.focus()
  })
}

function closeModal() {
  isOpen.value = false
  previouslyFocused.value?.focus()
}
```

### Form Validation

When validation errors occur:

1. Announce the error summary
2. Move focus to the first error field
3. Associate error messages with fields

```typescript
function handleSubmit() {
  const errors = validate(formData)
  
  if (errors.length > 0) {
    // Announce errors
    const errorSummary = `${errors.length} errors found. Please correct them.`
    announceToScreenReader(errorSummary)
    
    // Focus first error field
    const firstErrorField = document.getElementById(errors[0].fieldId)
    firstErrorField?.focus()
  }
}
```

### Dynamic Content

When content updates dynamically:

1. Use ARIA live regions for announcements
2. Don't move focus unexpectedly
3. Provide loading state announcements

```html
<div aria-live="polite" aria-busy="false">
  <p v-if="isLoading">Loading profiles...</p>
  <p v-else-if="error">Error: {{ error.message }}</p>
  <ul v-else>
    <li v-for="profile in profiles" :key="profile.id">
      {{ profile.name }}
    </li>
  </ul>
</div>
```

---

## Testing Checklist

### Automated Testing

- [ ] Run axe-core on all pages
- [ ] Validate HTML with W3C validator
- [ ] Check color contrast with automated tools
- [ ] Test with ESLint a11y plugin

### Manual Testing

- [ ] Navigate entire app using only keyboard
- [ ] Test with screen reader (VoiceOver, NVDA, JAWS)
- [ ] Test at 200% zoom
- [ ] Test with high contrast mode
- [ ] Test with reduced motion preference
- [ ] Test on mobile with screen reader

### Screen Reader Testing Script

1. Navigate to home page
2. Use heading navigation to understand page structure
3. Tab through all interactive elements
4. Submit a form with errors
5. Open and close a modal
6. Navigate through a dropdown menu
7. Complete a multi-step flow

---

## Implementation Guidelines

### Vue Component Best Practices

```vue
<template>
  <button
    type="button"
    :aria-pressed="isActive"
    :aria-disabled="isDisabled"
    @click="handleClick"
    @keydown.enter="handleClick"
    @keydown.space.prevent="handleClick"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
defineProps<{
  isActive?: boolean
  isDisabled?: boolean
}>()

const emit = defineEmits<{
  click: []
}>()

function handleClick() {
  emit('click')
}
</script>
```

### Form Accessibility Pattern

```vue
<template>
  <div class="form-group" :class="{ 'has-error': error }">
    <label :for="id" class="form-label">
      {{ label }}
      <span v-if="required" aria-hidden="true">*</span>
    </label>
    <input
      :id="id"
      v-model="modelValue"
      :type="type"
      :aria-required="required"
      :aria-invalid="!!error"
      :aria-describedby="describedBy"
      class="form-input"
    />
    <p v-if="hint" :id="`${id}-hint`" class="form-hint">
      {{ hint }}
    </p>
    <p v-if="error" :id="`${id}-error`" class="form-error" role="alert">
      {{ error }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  id: string
  label: string
  modelValue: string
  type?: string
  required?: boolean
  hint?: string
  error?: string
}>()

const describedBy = computed(() => {
  const ids = []
  if (props.hint) ids.push(`${props.id}-hint`)
  if (props.error) ids.push(`${props.id}-error`)
  return ids.length ? ids.join(' ') : undefined
})
</script>
```

---

## Resources

### Documentation

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)

### Testing Tools

- [axe DevTools](https://www.deque.com/axe/devtools/)
- [WAVE Evaluation Tool](https://wave.webaim.org/)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [VoiceOver (macOS)](https://support.apple.com/guide/voiceover/welcome/mac)
- [NVDA (Windows)](https://www.nvaccess.org/)

### Vue Accessibility

- [Vue A11y](https://vue-a11y.com/)
- [HeadlessUI](https://headlessui.com/) (already installed)
