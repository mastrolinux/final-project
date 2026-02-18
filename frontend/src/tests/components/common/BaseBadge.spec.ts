/**
 * Unit tests for BaseBadge component.
 *
 * Tests verify variant classes, size classes, default props,
 * and slot content rendering.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseBadge from '@/components/common/BaseBadge.vue'

describe('BaseBadge', () => {
  it('should render slot content', () => {
    const wrapper = mount(BaseBadge, {
      slots: { default: 'Active' }
    })

    expect(wrapper.text()).toBe('Active')
  })

  it('should apply default variant (neutral) and size (md)', () => {
    const wrapper = mount(BaseBadge, {
      slots: { default: 'Badge' }
    })

    expect(wrapper.classes()).toContain('badge')
    expect(wrapper.classes()).toContain('badge-neutral')
    expect(wrapper.classes()).toContain('badge-md')
  })

  it('should apply variant class', () => {
    const wrapper = mount(BaseBadge, {
      props: { variant: 'success' },
      slots: { default: 'Success' }
    })

    expect(wrapper.classes()).toContain('badge-success')
  })

  it('should apply size class', () => {
    const wrapper = mount(BaseBadge, {
      props: { size: 'sm' },
      slots: { default: 'Small' }
    })

    expect(wrapper.classes()).toContain('badge-sm')
  })

  it('should support context type variants', () => {
    const wrapper = mount(BaseBadge, {
      props: { variant: 'professional' },
      slots: { default: 'Professional' }
    })

    expect(wrapper.classes()).toContain('badge-professional')
  })

  it('should render as a span element', () => {
    const wrapper = mount(BaseBadge, {
      slots: { default: 'Tag' }
    })

    expect(wrapper.element.tagName).toBe('SPAN')
  })
})
