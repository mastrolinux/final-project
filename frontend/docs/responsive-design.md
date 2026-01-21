# Responsive Design Specification

This document defines the responsive design strategy for the Identity Management frontend application. The design follows a mobile-first approach with progressive enhancement for larger screens.

## Breakpoint System

### Breakpoint Definitions

| Name | Min Width | Target Devices |
|------|-----------|----------------|
| Mobile | 0px | Phones (portrait) |
| Mobile Landscape | 480px | Phones (landscape) |
| Tablet | 640px | Tablets (portrait), large phones |
| Tablet Landscape | 768px | Tablets (landscape) |
| Desktop | 1024px | Laptops, small monitors |
| Desktop Large | 1280px | Desktop monitors |
| Desktop XL | 1536px | Large monitors, wide screens |

### CSS Custom Properties

```css
:root {
  /* Breakpoint values for reference */
  --breakpoint-sm: 480px;
  --breakpoint-md: 640px;
  --breakpoint-lg: 768px;
  --breakpoint-xl: 1024px;
  --breakpoint-2xl: 1280px;
  --breakpoint-3xl: 1536px;
}
```

### Media Query Usage

```css
/* Mobile first - base styles */
.component {
  padding: var(--spacing-4);
}

/* Tablet and up */
@media (min-width: 640px) {
  .component {
    padding: var(--spacing-6);
  }
}

/* Desktop and up */
@media (min-width: 1024px) {
  .component {
    padding: var(--spacing-8);
  }
}
```

---

## Layout Patterns

### Container

The main content container adapts to screen size:

| Breakpoint | Max Width | Side Padding |
|------------|-----------|--------------|
| Mobile | 100% | 16px |
| Tablet | 100% | 24px |
| Desktop | 1024px | 32px |
| Desktop Large | 1280px | 32px |

```css
.container {
  width: 100%;
  margin-left: auto;
  margin-right: auto;
  padding-left: var(--spacing-4);
  padding-right: var(--spacing-4);
}

@media (min-width: 640px) {
  .container {
    padding-left: var(--spacing-6);
    padding-right: var(--spacing-6);
  }
}

@media (min-width: 1024px) {
  .container {
    max-width: 1024px;
    padding-left: var(--spacing-8);
    padding-right: var(--spacing-8);
  }
}

@media (min-width: 1280px) {
  .container {
    max-width: 1280px;
  }
}
```

### Grid System

A flexible grid system for content layout:

```css
.grid {
  display: grid;
  gap: var(--spacing-4);
  grid-template-columns: 1fr;
}

/* 2 columns on tablet */
@media (min-width: 640px) {
  .grid-cols-2 {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 3 columns on desktop */
@media (min-width: 1024px) {
  .grid-cols-3 {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* 4 columns on large desktop */
@media (min-width: 1280px) {
  .grid-cols-4 {
    grid-template-columns: repeat(4, 1fr);
  }
}
```

### Stack Layout

Vertical stacking with consistent spacing:

```css
.stack {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.stack-sm { gap: var(--spacing-2); }
.stack-lg { gap: var(--spacing-6); }
.stack-xl { gap: var(--spacing-8); }
```

---

## Navigation Patterns

### Header Navigation

| Breakpoint | Layout | Behavior |
|------------|--------|----------|
| Mobile | Logo + hamburger | Menu opens as full-screen overlay |
| Tablet | Logo + hamburger | Menu opens as slide-out panel |
| Desktop | Logo + horizontal nav + user menu | All items visible |

#### Mobile Navigation

```html
<header class="header">
  <div class="header-content">
    <a href="/" class="header-logo">Identity</a>
    
    <!-- Mobile menu button -->
    <button 
      class="header-menu-button" 
      aria-expanded="false"
      aria-controls="mobile-menu"
      aria-label="Open menu"
    >
      <MenuIcon />
    </button>
    
    <!-- Desktop navigation -->
    <nav class="header-nav-desktop" aria-label="Main navigation">
      <a href="/profile">Profile</a>
      <a href="/contexts">Contexts</a>
      <a href="/settings">Settings</a>
    </nav>
  </div>
</header>

<!-- Mobile menu overlay -->
<div id="mobile-menu" class="mobile-menu" aria-hidden="true">
  <nav aria-label="Main navigation">
    <a href="/profile">Profile</a>
    <a href="/contexts">Contexts</a>
    <a href="/settings">Settings</a>
  </nav>
</div>
```

```css
.header-nav-desktop {
  display: none;
}

.header-menu-button {
  display: flex;
}

@media (min-width: 1024px) {
  .header-nav-desktop {
    display: flex;
    gap: var(--spacing-6);
  }
  
  .header-menu-button {
    display: none;
  }
}
```

### Sidebar Navigation

For settings and complex pages:

| Breakpoint | Layout |
|------------|--------|
| Mobile | Tabs or accordion at top |
| Tablet | Collapsible sidebar |
| Desktop | Fixed sidebar (280px) |

```css
.sidebar-layout {
  display: flex;
  flex-direction: column;
}

.sidebar {
  width: 100%;
  border-bottom: 1px solid var(--border-primary);
}

.sidebar-content {
  width: 100%;
}

@media (min-width: 768px) {
  .sidebar-layout {
    flex-direction: row;
  }
  
  .sidebar {
    width: 200px;
    flex-shrink: 0;
    border-bottom: none;
    border-right: 1px solid var(--border-primary);
  }
  
  .sidebar-content {
    flex: 1;
    min-width: 0;
  }
}

@media (min-width: 1024px) {
  .sidebar {
    width: 280px;
  }
}
```

---

## Component Adaptations

### Cards

| Breakpoint | Layout |
|------------|--------|
| Mobile | Full width, stacked |
| Tablet | 2 columns |
| Desktop | 3 columns |

```css
.card-grid {
  display: grid;
  gap: var(--spacing-4);
  grid-template-columns: 1fr;
}

@media (min-width: 640px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .card-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

### Forms

| Breakpoint | Layout |
|------------|--------|
| Mobile | Single column, full width inputs |
| Tablet | Two-column for related fields |
| Desktop | Optimized width (max 600px) |

```css
.form {
  width: 100%;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

@media (min-width: 640px) {
  .form-row {
    flex-direction: row;
  }
  
  .form-row > * {
    flex: 1;
  }
}

@media (min-width: 1024px) {
  .form {
    max-width: 600px;
  }
}
```

### Tables

| Breakpoint | Layout |
|------------|--------|
| Mobile | Card-based or horizontal scroll |
| Tablet | Condensed table |
| Desktop | Full table with all columns |

```html
<!-- Mobile: Card layout -->
<div class="table-mobile">
  <div class="table-card" v-for="item in items">
    <div class="table-card-row">
      <span class="table-card-label">Name</span>
      <span class="table-card-value">{{ item.name }}</span>
    </div>
    <!-- More rows -->
  </div>
</div>

<!-- Desktop: Traditional table -->
<table class="table-desktop">
  <thead>
    <tr>
      <th>Name</th>
      <th>Type</th>
      <th>Status</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr v-for="item in items">
      <td>{{ item.name }}</td>
      <td>{{ item.type }}</td>
      <td>{{ item.status }}</td>
      <td><!-- Actions --></td>
    </tr>
  </tbody>
</table>
```

```css
.table-mobile {
  display: block;
}

.table-desktop {
  display: none;
}

@media (min-width: 768px) {
  .table-mobile {
    display: none;
  }
  
  .table-desktop {
    display: table;
    width: 100%;
  }
}
```

### Modals

| Breakpoint | Layout |
|------------|--------|
| Mobile | Full screen |
| Tablet | Centered, 90% width |
| Desktop | Centered, max 500px |

```css
.modal {
  position: fixed;
  inset: 0;
  background: var(--bg-secondary);
  padding: var(--spacing-4);
  overflow-y: auto;
}

@media (min-width: 640px) {
  .modal {
    inset: auto;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 90%;
    max-width: 500px;
    max-height: 90vh;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-xl);
  }
}
```

### Buttons

| Breakpoint | Layout |
|------------|--------|
| Mobile | Full width or stacked |
| Tablet+ | Inline, natural width |

```css
.button-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.button-group .btn {
  width: 100%;
}

@media (min-width: 640px) {
  .button-group {
    flex-direction: row;
    justify-content: flex-end;
  }
  
  .button-group .btn {
    width: auto;
  }
}
```

---

## Touch Target Sizes

### Minimum Sizes

All interactive elements must meet minimum touch target sizes:

| Element | Minimum Size | Recommended |
|---------|--------------|-------------|
| Buttons | 44x44px | 48x48px |
| Links (inline) | 44px height | 48px height |
| Form inputs | 44px height | 48px height |
| Checkboxes/Radios | 44x44px tap area | 48x48px |
| Close buttons | 44x44px | 48x48px |

### Implementation

```css
/* Button minimum size */
.btn {
  min-height: 44px;
  min-width: 44px;
  padding: var(--spacing-3) var(--spacing-4);
}

/* Input minimum size */
.form-input,
.form-select {
  min-height: 44px;
  padding: var(--spacing-3);
}

/* Checkbox tap area */
.form-checkbox {
  position: relative;
  min-height: 44px;
  display: flex;
  align-items: center;
}

.form-checkbox input {
  position: absolute;
  width: 44px;
  height: 44px;
  opacity: 0;
  cursor: pointer;
}

/* Icon button */
.btn-icon {
  width: 44px;
  height: 44px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Larger on mobile for easier tapping */
@media (max-width: 639px) {
  .btn {
    min-height: 48px;
  }
  
  .form-input,
  .form-select {
    min-height: 48px;
  }
}
```

### Spacing Between Targets

Ensure adequate spacing between touch targets:

```css
/* Minimum 8px between touch targets */
.nav-links {
  display: flex;
  gap: var(--spacing-2);
}

.nav-links a {
  padding: var(--spacing-3);
}

/* List items */
.list-item {
  padding: var(--spacing-3) var(--spacing-4);
}

.list-item + .list-item {
  border-top: 1px solid var(--border-primary);
}
```

---

## Typography Scaling

### Fluid Typography

Font sizes scale smoothly between breakpoints:

```css
:root {
  /* Base size: 16px */
  font-size: 100%;
}

/* Headings scale with viewport */
h1 {
  font-size: clamp(1.75rem, 4vw + 1rem, 2.25rem);
}

h2 {
  font-size: clamp(1.5rem, 3vw + 0.75rem, 1.875rem);
}

h3 {
  font-size: clamp(1.25rem, 2vw + 0.5rem, 1.5rem);
}
```

### Line Length

Optimal line length for readability:

```css
/* Prose content */
.prose {
  max-width: 65ch;
}

/* Form labels */
.form-label {
  max-width: 45ch;
}
```

---

## Image Handling

### Responsive Images

```html
<picture>
  <source 
    media="(min-width: 1024px)" 
    srcset="hero-desktop.jpg"
  >
  <source 
    media="(min-width: 640px)" 
    srcset="hero-tablet.jpg"
  >
  <img 
    src="hero-mobile.jpg" 
    alt="Hero image"
    loading="lazy"
  >
</picture>
```

### Avatar Sizes

| Breakpoint | Size |
|------------|------|
| Mobile | 40px |
| Tablet | 48px |
| Desktop | 56px |

```css
.avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
}

@media (min-width: 640px) {
  .avatar {
    width: 48px;
    height: 48px;
  }
}

@media (min-width: 1024px) {
  .avatar {
    width: 56px;
    height: 56px;
  }
}
```

---

## Page-Specific Layouts

### Home Page

| Breakpoint | Layout |
|------------|--------|
| Mobile | Stacked: hero, features, CTA |
| Tablet | Hero with side illustration |
| Desktop | Full hero with background, 3-column features |

### Profile Page

| Breakpoint | Layout |
|------------|--------|
| Mobile | Avatar top, info stacked below |
| Tablet | Avatar left, info right (2 columns) |
| Desktop | Sidebar navigation + content area |

### Contexts List

| Breakpoint | Layout |
|------------|--------|
| Mobile | Card stack, 1 column |
| Tablet | Card grid, 2 columns |
| Desktop | Card grid, 3 columns with filters sidebar |

### OAuth Consent

| Breakpoint | Layout |
|------------|--------|
| Mobile | Full screen, stacked content |
| Tablet | Centered card, 80% width |
| Desktop | Centered card, max 500px |

---

## Testing Checklist

### Device Testing

- [ ] iPhone SE (375px)
- [ ] iPhone 14 (390px)
- [ ] iPhone 14 Pro Max (430px)
- [ ] iPad Mini (768px)
- [ ] iPad Pro (1024px)
- [ ] MacBook Air (1280px)
- [ ] Desktop monitor (1920px)

### Orientation Testing

- [ ] Portrait orientation
- [ ] Landscape orientation
- [ ] Orientation change handling

### Interaction Testing

- [ ] Touch targets are easily tappable
- [ ] Hover states don't interfere with touch
- [ ] Scrolling is smooth
- [ ] No horizontal overflow

### Content Testing

- [ ] Text is readable at all sizes
- [ ] Images scale appropriately
- [ ] Forms are usable on mobile
- [ ] Tables are accessible on mobile

---

## CSS Utilities

### Responsive Display

```css
.hidden { display: none; }
.block { display: block; }
.flex { display: flex; }

@media (min-width: 640px) {
  .md\:hidden { display: none; }
  .md\:block { display: block; }
  .md\:flex { display: flex; }
}

@media (min-width: 1024px) {
  .lg\:hidden { display: none; }
  .lg\:block { display: block; }
  .lg\:flex { display: flex; }
}
```

### Responsive Spacing

```css
.p-4 { padding: var(--spacing-4); }

@media (min-width: 640px) {
  .md\:p-6 { padding: var(--spacing-6); }
}

@media (min-width: 1024px) {
  .lg\:p-8 { padding: var(--spacing-8); }
}
```

### Responsive Text

```css
.text-center { text-align: center; }
.text-left { text-align: left; }

@media (min-width: 640px) {
  .md\:text-left { text-align: left; }
}
```

---

## Performance Considerations

### Critical CSS

Inline critical CSS for above-the-fold content to prevent layout shifts.

### Image Optimization

- Use WebP format with fallbacks
- Implement lazy loading for below-fold images
- Use appropriate image sizes for each breakpoint

### Font Loading

- Use `font-display: swap` for web fonts
- Preload critical fonts
- Use system fonts as fallback

```css
@font-face {
  font-family: 'CustomFont';
  src: url('/fonts/custom.woff2') format('woff2');
  font-display: swap;
}
```

### Reduce Motion

Respect user preferences for reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```
