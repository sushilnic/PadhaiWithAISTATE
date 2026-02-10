# PadhaiWithAI - Unified Theme Guide

## 🎨 Theme Overview

A clean, modern, and simple theme with a teal-based color palette designed for educational applications. The theme emphasizes clarity, professionalism, and ease of use.

---

## 📋 Color Palette

### Primary Colors
| Name | Hex | Usage |
|------|-----|-------|
| **Primary** | `#14B8A6` | Main buttons, headers, links, accents |
| **Primary Dark** | `#0D9488` | Hover states, gradients |
| **Primary Light** | `#2DD4BF` | Light backgrounds, overlays |

### Secondary & Utility Colors
| Name | Hex | Usage |
|------|-----|-------|
| **Secondary** | `#64748B` | Secondary text, disabled states |
| **Accent** | `#F59E0B` | Highlights (currently reserved for future use) |
| **Success** | `#10B981` | Success messages, positive actions |
| **Info** | `#06B6D4` | Info badges, secondary highlights |
| **Danger** | `#EF4444` | Delete buttons, error states |

### Neutral Colors
| Name | Hex | Usage |
|------|-----|-------|
| **Background** | `#F8FAFC` | Page background, light surfaces |
| **Surface** | `#FFFFFF` | Cards, containers, main surfaces |
| **Text Primary** | `#1E293B` | Main text content |
| **Text Secondary** | `#64748B` | Secondary text, descriptions |
| **Border** | `#E2E8F0` | Dividers, borders, subtle lines |

---

## 🎯 Key Design Principles

### 1. **Simplicity**
- Minimal visual clutter
- Clear hierarchy and typography
- Consistent spacing and alignment

### 2. **Professionalism**
- Clean gradients (teal primary colors)
- Subtle shadows for depth
- Smooth transitions and animations

### 3. **Accessibility**
- High contrast ratios for text readability
- Clear button states and hover effects
- Responsive design for all devices

### 4. **Consistency**
- Unified color usage across all pages
- Standard border radius: `8px` to `12px`
- Consistent padding: `15px` to `20px`

---

## 🔧 CSS Variables Implementation

All color values are defined as CSS custom properties (variables) in the `:root` selector:

```css
:root {
    --primary: #14B8A6;
    --primary-dark: #0D9488;
    --primary-light: #2DD4BF;
    --secondary: #64748B;
    --accent: #F59E0B;
    --background: #F8FAFC;
    --surface: #FFFFFF;
    --text-primary: #1E293B;
    --text-secondary: #64748B;
    --border: #E2E8F0;
    --success: #10B981;
    --danger: #EF4444;
    --info: #06B6D4;
}
```

**Usage in Stylesheets:**
```css
.button {
    background-color: var(--primary);
    color: white;
}

.button:hover {
    background-color: var(--primary-dark);
}
```

---

## 📐 Spacing & Layout

### Standard Padding
- **Containers**: `40px 30px` (large sections)
- **Cards**: `20px` (internal padding)
- **Table cells**: `15px 20px`
- **Buttons**: `12px 25px`

### Standard Border Radius
- **Large elements**: `15px` (headers, containers)
- **Standard elements**: `12px` (cards, boxes)
- **Buttons**: `8px`
- **Badges**: `20px` (pill-shaped)

### Grid Layouts
```css
/* Responsive card grid */
grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));

/* Desktop: 3 columns, Tablet: 2 columns, Mobile: 1 column */
```

---

## 🎨 Component Styles

### Buttons

**Primary Button**
```css
background-color: var(--primary);
color: white;
border: none;
font-weight: 600;
border-radius: 8px;
```

**Primary Button Hover**
```css
background-color: var(--primary-dark);
transform: translateY(-2px);
box-shadow: 0 6px 15px rgba(0, 0, 0, 0.15);
```

### Cards

**Standard Card**
```css
background: var(--surface);
border-radius: 12px;
box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
border: 1px solid var(--border);
```

**Card Header Gradient**
```css
background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
color: white;
```

### Tables

**Table Header**
```css
background-color: var(--primary);
color: white;
```

**Table Row Hover**
```css
background-color: #F0FDFA; /* Light teal background */
transition: all 0.2s ease;
```

### Inputs & Forms

**Input Focus**
```css
border-color: var(--primary);
box-shadow: 0 0 10px rgba(20, 184, 166, 0.1);
outline: none;
```

---

## ✨ Animations

### Fade In Up
```css
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Apply with staggered delays */
.card {
    animation: fadeInUp 0.5s ease-in-out;
}

.card:nth-child(1) { animation-delay: 0.1s; }
.card:nth-child(2) { animation-delay: 0.2s; }
.card:nth-child(3) { animation-delay: 0.3s; }
```

### Hover Effects
- **Scale**: `transform: scale(1.01)` on hover
- **Translate**: `transform: translateY(-2px)` on buttons
- **Transition**: `all 0.3s ease` for smooth movement

---

## 📱 Responsive Breakpoints

### Desktop
- Width: `1200px+`
- Grid: 3-4 columns for card layouts
- Full sidebar display

### Tablet
- Width: `768px - 1199px`
- Grid: 2 columns for card layouts
- Adjusted font sizes

### Mobile
- Width: `< 768px`
- Grid: 1 column (stacked)
- Compact buttons, reduced padding
- Single-column layouts

---

## 🔄 Gradient Usage

### Primary Gradient (Main CTA)
```css
background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
```
**Angle**: 135° (diagonal top-left to bottom-right)
**Used for**: Headers, action buttons, featured sections

### Secondary Gradients
```css
background: linear-gradient(135deg, var(--info) 0%, #0891b2 100%);
```
**Used for**: Info badges, secondary highlights

---

## 📝 Typography

### Font Stack
```css
font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
```

### Font Weights
- **Regular**: `400` (body text)
- **Medium**: `500` (labels, secondary headings)
- **Semibold**: `600` (buttons, strong text)
- **Bold**: `700` (headings, emphasized content)

### Font Sizes
- **H1**: `2.5rem - 2.8rem` (page titles)
- **H3**: `1.4rem` (section headers)
- **Regular text**: `0.95rem - 1rem`
- **Small text**: `0.85rem - 0.9rem`

---

## 🎓 Templates Using This Theme

### 1. **theme.html**
Base template with navbar and footer styling
- Primary color navbar
- Clean footer with light background

### 2. **student_list.html**
Student management page
- Teal gradient header
- Responsive table with hover states
- Modern search functionality

### 3. **school_student_list.html**
School-wise student report
- Teal card-based layout
- Staggered animations
- Real-time search across schools and students

---

## 🚀 How to Apply Theme Globally

### Step 1: Define Root Variables
Add to your main CSS or base template:
```css
:root {
    --primary: #14B8A6;
    --primary-dark: #0D9488;
    --secondary: #64748B;
    /* ... other colors ... */
}
```

### Step 2: Use Variables in Components
```css
.navbar {
    background-color: var(--surface);
    border-bottom: 2px solid var(--border);
}

.btn-primary {
    background-color: var(--primary);
}

.btn-primary:hover {
    background-color: var(--primary-dark);
}
```

### Step 3: Maintain Consistency
- Always use variables instead of hardcoded colors
- Follow the spacing guidelines
- Apply hover effects consistently
- Use proper border-radius values

---

## 🎯 Best Practices

1. **Always use CSS variables** for colors - makes theme changes easy
2. **Test on mobile** - ensure responsive design works
3. **Maintain hover states** - important for UX
4. **Use consistent spacing** - creates visual harmony
5. **Apply animations subtly** - avoid overwhelming users
6. **Keep contrast high** - ensure text readability
7. **Respect the color palette** - use suggested colors only

---

## 🔄 Future Theme Updates

To update the entire theme, simply modify the CSS variables in `:root`:
- All colors will update automatically
- No need to modify individual component styles
- Changes propagate across all pages instantly

---

**Last Updated**: February 3, 2026  
**Theme Version**: 1.0  
**Color Palette**: Teal-based Professional  
