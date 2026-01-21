# Design System

The design system ensures consistency across all components and pages while supporting theming (light/dark mode) and accessibility requirements.

## Design Tokens

Design tokens are defined as CSS custom properties in `src/assets/styles/variables.css`. This enables runtime theming and consistent values across the application.

### Color Palette

#### Primary Colors (Blue)

Used for primary actions, links, and focus states.

| Token | Light Mode | Usage |
|-------|------------|-------|
| `--color-primary-50` | #eff6ff | Backgrounds, hover states |
| `--color-primary-100` | #dbeafe | Light backgrounds |
| `--color-primary-200` | #bfdbfe | Borders, dividers |
| `--color-primary-300` | #93c5fd | Disabled states |
| `--color-primary-400` | #60a5fa | Secondary text |
| `--color-primary-500` | #3b82f6 | Primary color |
| `--color-primary-600` | #2563eb | Primary actions |
| `--color-primary-700` | #1d4ed8 | Hover states |
| `--color-primary-800` | #1e40af | Active states |
| `--color-primary-900` | #1e3a8a | Text on light backgrounds |

#### Neutral Colors (Gray)

Used for text, backgrounds, and borders.

| Token | Value | Usage |
|-------|-------|-------|
| `--color-gray-50` | #f9fafb | Page backgrounds |
| `--color-gray-100` | #f3f4f6 | Card backgrounds |
| `--color-gray-200` | #e5e7eb | Borders |
| `--color-gray-300` | #d1d5db | Input borders |
| `--color-gray-400` | #9ca3af | Placeholder text |
| `--color-gray-500` | #6b7280 | Secondary text |
| `--color-gray-600` | #4b5563 | Body text |
| `--color-gray-700` | #374151 | Headings |
| `--color-gray-800` | #1f2937 | Dark backgrounds |
| `--color-gray-900` | #111827 | Primary text |

#### Semantic Colors

Used for status indicators and feedback.

| Category | Token | Value | Usage |
|----------|-------|-------|-------|
| Success | `--color-success-50` | #f0fdf4 | Success backgrounds |
| Success | `--color-success-500` | #22c55e | Success icons, text |
| Success | `--color-success-700` | #15803d | Success text on light |
| Warning | `--color-warning-50` | #fffbeb | Warning backgrounds |
| Warning | `--color-warning-500` | #f59e0b | Warning icons, text |
| Warning | `--color-warning-700` | #b45309 | Warning text on light |
| Error | `--color-error-50` | #fef2f2 | Error backgrounds |
| Error | `--color-error-500` | #ef4444 | Error icons, text |
| Error | `--color-error-700` | #b91c1c | Error text on light |
| Info | `--color-info-50` | #eff6ff | Info backgrounds |
| Info | `--color-info-500` | #3b82f6 | Info icons, text |
| Info | `--color-info-700` | #1d4ed8 | Info text on light |

#### Context Type Colors

Each identity context type has a distinct color for visual identification.

| Context Type | Token | Value | Usage |
|--------------|-------|-------|-------|
| Professional | `--color-context-professional` | #3b82f6 | Blue - work contexts |
| Social | `--color-context-social` | #a855f7 | Purple - social contexts |
| Legal | `--color-context-legal` | #22c55e | Green - legal contexts |
| Healthcare | `--color-context-healthcare` | #ef4444 | Red - healthcare contexts |
| Family | `--color-context-family` | #f59e0b | Amber - family contexts |
| Custom | `--color-context-custom` | #6b7280 | Gray - custom contexts |

### Typography

#### Font Families

```css
--font-family-sans: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
--font-family-mono: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
```

#### Font Sizes

| Token | Size | Usage |
|-------|------|-------|
| `--font-size-xs` | 0.75rem (12px) | Captions, labels |
| `--font-size-sm` | 0.875rem (14px) | Secondary text, buttons |
| `--font-size-base` | 1rem (16px) | Body text |
| `--font-size-lg` | 1.125rem (18px) | Large body text |
| `--font-size-xl` | 1.25rem (20px) | Small headings |
| `--font-size-2xl` | 1.5rem (24px) | Section headings |
| `--font-size-3xl` | 1.875rem (30px) | Page headings |
| `--font-size-4xl` | 2.25rem (36px) | Hero headings |

#### Font Weights

| Token | Weight | Usage |
|-------|--------|-------|
| `--font-weight-normal` | 400 | Body text |
| `--font-weight-medium` | 500 | Emphasized text |
| `--font-weight-semibold` | 600 | Subheadings |
| `--font-weight-bold` | 700 | Headings |

#### Line Heights

| Token | Value | Usage |
|-------|-------|-------|
| `--line-height-tight` | 1.25 | Headings |
| `--line-height-normal` | 1.5 | Body text |
| `--line-height-relaxed` | 1.75 | Long-form content |

### Spacing Scale

Consistent spacing using a 4px base unit.

| Token | Value | Usage |
|-------|-------|-------|
| `--spacing-0` | 0 | No spacing |
| `--spacing-1` | 0.25rem (4px) | Tight spacing |
| `--spacing-2` | 0.5rem (8px) | Small gaps |
| `--spacing-3` | 0.75rem (12px) | Input padding |
| `--spacing-4` | 1rem (16px) | Default spacing |
| `--spacing-5` | 1.25rem (20px) | Medium spacing |
| `--spacing-6` | 1.5rem (24px) | Section spacing |
| `--spacing-8` | 2rem (32px) | Large spacing |
| `--spacing-10` | 2.5rem (40px) | Extra large |
| `--spacing-12` | 3rem (48px) | Section gaps |
| `--spacing-16` | 4rem (64px) | Page sections |
| `--spacing-20` | 5rem (80px) | Hero spacing |

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 0.125rem (2px) | Subtle rounding |
| `--radius-md` | 0.375rem (6px) | Buttons, inputs |
| `--radius-lg` | 0.5rem (8px) | Cards |
| `--radius-xl` | 0.75rem (12px) | Modals |
| `--radius-2xl` | 1rem (16px) | Large cards |
| `--radius-full` | 9999px | Pills, avatars |

### Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | 0 1px 2px 0 rgb(0 0 0 / 0.05) | Subtle elevation |
| `--shadow-md` | 0 4px 6px -1px rgb(0 0 0 / 0.1)... | Cards, dropdowns |
| `--shadow-lg` | 0 10px 15px -3px rgb(0 0 0 / 0.1)... | Modals |
| `--shadow-xl` | 0 20px 25px -5px rgb(0 0 0 / 0.1)... | Popovers |

### Transitions

| Token | Value | Usage |
|-------|-------|-------|
| `--transition-fast` | 150ms ease | Hover states |
| `--transition-normal` | 200ms ease | Default transitions |
| `--transition-slow` | 300ms ease | Complex animations |

### Z-Index Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--z-dropdown` | 1000 | Dropdown menus |
| `--z-sticky` | 1020 | Sticky headers |
| `--z-fixed` | 1030 | Fixed elements |
| `--z-modal-backdrop` | 1040 | Modal overlays |
| `--z-modal` | 1050 | Modal dialogs |
| `--z-popover` | 1060 | Popovers |
| `--z-tooltip` | 1070 | Tooltips |
| `--z-toast` | 1080 | Toast notifications |

### Layout

| Token | Value | Usage |
|-------|-------|-------|
| `--container-max-width` | 1280px | Max content width |
| `--sidebar-width` | 280px | Sidebar width |
| `--header-height` | 64px | Header height |

---

## Component Patterns

### Buttons

#### Button Variants

```html
<!-- Primary Button -->
<button class="btn btn-primary">Primary Action</button>

<!-- Secondary Button -->
<button class="btn btn-secondary">Secondary Action</button>

<!-- Danger Button -->
<button class="btn btn-danger">Delete</button>

<!-- Ghost Button -->
<button class="btn btn-ghost">Cancel</button>
```

#### Button Sizes

```html
<button class="btn btn-primary btn-sm">Small</button>
<button class="btn btn-primary">Default</button>
<button class="btn btn-primary btn-lg">Large</button>
```

#### Button States

| State | Visual Treatment |
|-------|------------------|
| Default | Solid background, normal cursor |
| Hover | Darker background, pointer cursor |
| Focus | Focus ring (2px primary color offset) |
| Active | Even darker background |
| Disabled | Reduced opacity (0.5), not-allowed cursor |
| Loading | Spinner icon, disabled interaction |

### Form Inputs

#### Text Input

```html
<div class="form-group">
  <label for="email" class="form-label">Email</label>
  <input type="email" id="email" class="form-input" placeholder="Enter your email">
  <p class="form-hint">We'll never share your email.</p>
</div>
```

#### Input States

| State | Visual Treatment |
|-------|------------------|
| Default | Gray border |
| Focus | Primary color border, focus ring |
| Error | Error color border, error message below |
| Disabled | Gray background, reduced opacity |
| Read-only | No border, gray background |

#### Select Input

```html
<div class="form-group">
  <label for="context" class="form-label">Context Type</label>
  <select id="context" class="form-select">
    <option value="">Select a type</option>
    <option value="professional">Professional</option>
    <option value="social">Social</option>
  </select>
</div>
```

#### Checkbox and Radio

```html
<!-- Checkbox -->
<label class="form-checkbox">
  <input type="checkbox">
  <span>Remember this decision</span>
</label>

<!-- Radio -->
<label class="form-radio">
  <input type="radio" name="type" value="verified">
  <span>Verified Account</span>
</label>
```

### Cards

```html
<div class="card">
  <div class="card-header">
    <h3>Card Title</h3>
  </div>
  <div class="card-body">
    <p>Card content goes here.</p>
  </div>
  <div class="card-footer">
    <button class="btn btn-secondary">Cancel</button>
    <button class="btn btn-primary">Save</button>
  </div>
</div>
```

### Modals

```html
<div class="modal-backdrop" aria-hidden="true"></div>
<div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <div class="modal-header">
    <h2 id="modal-title">Modal Title</h2>
    <button class="modal-close" aria-label="Close">X</button>
  </div>
  <div class="modal-body">
    <p>Modal content goes here.</p>
  </div>
  <div class="modal-footer">
    <button class="btn btn-secondary">Cancel</button>
    <button class="btn btn-primary">Confirm</button>
  </div>
</div>
```

### Badges

```html
<!-- Status badges -->
<span class="badge badge-success">Verified</span>
<span class="badge badge-warning">Pending</span>
<span class="badge badge-error">Expired</span>

<!-- Context type badges -->
<span class="badge badge-professional">Professional</span>
<span class="badge badge-social">Social</span>
<span class="badge badge-legal">Legal</span>
```

---

## Feedback Patterns

### Toast Notifications

Used for transient feedback that doesn't require user action.

```html
<div class="toast toast-success" role="alert">
  <span class="toast-message">Profile saved successfully</span>
  <button class="toast-close" aria-label="Dismiss">X</button>
</div>
```

#### Toast Types

| Type | Color | Duration | Usage |
|------|-------|----------|-------|
| Success | Green | 5 seconds | Successful actions |
| Error | Red | 8 seconds | Failed actions |
| Warning | Amber | 5 seconds | Warnings |
| Info | Blue | 5 seconds | Information |

### Inline Validation

Used for form field validation feedback.

```html
<div class="form-group has-error">
  <label for="email" class="form-label">Email</label>
  <input type="email" id="email" class="form-input" aria-invalid="true" aria-describedby="email-error">
  <p id="email-error" class="form-error">Please enter a valid email address</p>
</div>
```

### Alert Banners

Used for page-level messages.

```html
<div class="alert alert-warning" role="alert">
  <strong>Warning:</strong> Your email is not verified. 
  <a href="/verify-email">Verify now</a>
</div>
```

---

## Loading States

### Spinner

```html
<div class="spinner" aria-label="Loading"></div>
<div class="spinner spinner-sm"></div>
<div class="spinner spinner-lg"></div>
```

### Skeleton Loading

```html
<div class="skeleton skeleton-text"></div>
<div class="skeleton skeleton-avatar"></div>
<div class="skeleton skeleton-card"></div>
```

### Button Loading

```html
<button class="btn btn-primary" disabled>
  <span class="spinner spinner-sm"></span>
  Saving...
</button>
```

### Page Loading

```html
<div class="loading-screen">
  <div class="spinner spinner-lg"></div>
  <p>Loading...</p>
</div>
```

---

## Context Indicators

### Active Context Badge

Shows which identity context is currently active.

```html
<div class="context-indicator">
  <span class="context-badge context-professional">
    Professional
  </span>
  <button class="context-switch" aria-label="Switch context">
    Switch
  </button>
</div>
```

### Context Selector

Dropdown for switching between contexts.

```html
<div class="context-selector">
  <button class="context-selector-trigger" aria-expanded="false">
    <span class="context-badge context-professional">Professional</span>
    <span class="chevron-down"></span>
  </button>
  <ul class="context-selector-menu" role="listbox">
    <li role="option" aria-selected="true">
      <span class="context-badge context-professional">Professional</span>
    </li>
    <li role="option">
      <span class="context-badge context-social">Social</span>
    </li>
  </ul>
</div>
```

### Inheritance Indicator

Shows whether a field value is inherited or overridden.

```html
<!-- Inherited value -->
<div class="field-value inherited">
  <span class="field-label">Email</span>
  <span class="field-content">sarah@personal.com</span>
  <span class="inheritance-badge">Inherited</span>
</div>

<!-- Overridden value -->
<div class="field-value overridden">
  <span class="field-label">Email</span>
  <span class="field-content">dr.chen@hospital.org</span>
  <span class="inheritance-badge">Custom</span>
</div>
```

---

## Dark Mode

The design system supports dark mode through CSS custom properties. Dark mode is activated by adding the `.dark` class to the `<html>` element.

### Semantic Variables

Use semantic variables instead of direct color references:

| Variable | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--bg-primary` | gray-50 | gray-900 |
| `--bg-secondary` | white | gray-800 |
| `--bg-tertiary` | gray-100 | gray-700 |
| `--text-primary` | gray-900 | gray-50 |
| `--text-secondary` | gray-600 | gray-300 |
| `--border-primary` | gray-200 | gray-700 |

### Implementation

```css
/* Use semantic variables */
.card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  color: var(--text-primary);
}

/* Avoid direct color references */
.card {
  /* Don't do this */
  background-color: #ffffff;
  color: #111827;
}
```

---

## Iconography

### Icon Sizes

| Size | Dimensions | Usage |
|------|------------|-------|
| xs | 12x12px | Inline with small text |
| sm | 16x16px | Buttons, inputs |
| md | 20x20px | Default size |
| lg | 24x24px | Navigation, headings |
| xl | 32x32px | Feature icons |

### Icon Colors

Icons should inherit text color by default:

```css
.icon {
  color: currentColor;
}
```

### Icon Library

Use Heroicons (already installed via `@heroicons/vue`):

```vue
<template>
  <UserIcon class="icon icon-md" />
  <CheckCircleIcon class="icon icon-lg text-success" />
</template>

<script setup>
import { UserIcon, CheckCircleIcon } from '@heroicons/vue/24/outline'
</script>
```

---

## Animation Guidelines

### Timing Functions

| Name | Value | Usage |
|------|-------|-------|
| ease | ease | General transitions |
| ease-in | ease-in | Exit animations |
| ease-out | ease-out | Enter animations |
| ease-in-out | ease-in-out | Continuous animations |

### Duration Guidelines

| Duration | Usage |
|----------|-------|
| 150ms | Hover states, micro-interactions |
| 200ms | Default transitions |
| 300ms | Complex state changes |
| 500ms | Page transitions |

### Reduced Motion

Respect user preferences for reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Usage Guidelines

### Do

- Use design tokens instead of hard-coded values
- Use semantic color variables for theme support
- Follow the spacing scale for consistent layouts
- Use appropriate component patterns
- Test all states (hover, focus, disabled, error)

### Don't

- Hard-code colors, sizes, or spacing
- Create custom one-off styles
- Skip loading or error states
- Ignore dark mode compatibility
- Forget accessibility requirements
