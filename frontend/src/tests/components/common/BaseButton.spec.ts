/**
 * Unit tests for BaseButton component.
 *
 * Tests verify variant/size class application, disabled/loading states,
 * slot rendering, block mode, and button type attribute.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseButton from '@/components/common/BaseButton.vue'

describe('BaseButton', () => {
  it('should render slot content', () => {
    const wrapper = mount(BaseButton, {
      slots: { default: 'Click me' }
    })

    expect(wrapper.text()).toContain('Click me')
  })

  it('should apply variant class', () => {
    const wrapper = mount(BaseButton, {
      props: { variant: 'danger' }
    })

    expect(wrapper.classes()).toContain('btn-danger')
  })

  it('should default to primary variant', () => {
    const wrapper = mount(BaseButton)

    expect(wrapper.classes()).toContain('btn-primary')
  })

  it('should apply size class', () => {
    const wrapper = mount(BaseButton, {
      props: { size: 'lg' }
    })

    expect(wrapper.classes()).toContain('btn-lg')
  })

  it('should default to md size', () => {
    const wrapper = mount(BaseButton)

    expect(wrapper.classes()).toContain('btn-md')
  })

  it('should be disabled when disabled prop is true', () => {
    const wrapper = mount(BaseButton, {
      props: { disabled: true }
    })

    expect(wrapper.attributes('disabled')).toBeDefined()
    expect(wrapper.classes()).toContain('is-disabled')
  })

  it('should be disabled when loading is true', () => {
    const wrapper = mount(BaseButton, {
      props: { loading: true }
    })

    expect(wrapper.attributes('disabled')).toBeDefined()
    expect(wrapper.classes()).toContain('is-loading')
  })

  it('should show spinner when loading', () => {
    const wrapper = mount(BaseButton, {
      props: { loading: true }
    })

    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('should not show spinner when not loading', () => {
    const wrapper = mount(BaseButton, {
      props: { loading: false }
    })

    expect(wrapper.find('.spinner').exists()).toBe(false)
  })

  it('should set button type attribute', () => {
    const wrapper = mount(BaseButton, {
      props: { type: 'submit' }
    })

    expect(wrapper.attributes('type')).toBe('submit')
  })

  it('should default to button type', () => {
    const wrapper = mount(BaseButton)

    expect(wrapper.attributes('type')).toBe('button')
  })

  it('should apply block class when block prop is true', () => {
    const wrapper = mount(BaseButton, {
      props: { block: true }
    })

    expect(wrapper.classes()).toContain('w-full')
  })
})
