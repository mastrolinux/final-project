/**
 * Unit tests for BaseInput component.
 *
 * Tests verify label rendering, required asterisk, v-model emission,
 * error/hint display, and aria attributes for accessibility.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseInput from '@/components/common/BaseInput.vue'

describe('BaseInput', () => {
  const defaultProps = {
    id: 'test-input',
    modelValue: ''
  }

  it('should render label when provided', () => {
    const wrapper = mount(BaseInput, {
      props: { ...defaultProps, label: 'Email' }
    })

    const label = wrapper.find('label')
    expect(label.exists()).toBe(true)
    expect(label.text()).toContain('Email')
    expect(label.attributes('for')).toBe('test-input')
  })

  it('should not render label when not provided', () => {
    const wrapper = mount(BaseInput, {
      props: defaultProps
    })

    expect(wrapper.find('label').exists()).toBe(false)
  })

  it('should show required asterisk', () => {
    const wrapper = mount(BaseInput, {
      props: { ...defaultProps, label: 'Email', required: true }
    })

    expect(wrapper.find('.text-error').exists()).toBe(true)
    expect(wrapper.find('.text-error').text()).toBe('*')
  })

  it('should emit update:modelValue on input', async () => {
    const wrapper = mount(BaseInput, {
      props: defaultProps
    })

    const input = wrapper.find('input')
    await input.setValue('hello@example.com')

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['hello@example.com'])
  })

  it('should show error message with role=alert', () => {
    const wrapper = mount(BaseInput, {
      props: { ...defaultProps, error: 'Invalid email' }
    })

    const error = wrapper.find('.form-error')
    expect(error.exists()).toBe(true)
    expect(error.text()).toBe('Invalid email')
    expect(error.attributes('role')).toBe('alert')
  })

  it('should show hint when no error', () => {
    const wrapper = mount(BaseInput, {
      props: { ...defaultProps, hint: 'Enter your email' }
    })

    expect(wrapper.find('.form-hint').exists()).toBe(true)
    expect(wrapper.find('.form-hint').text()).toBe('Enter your email')
    expect(wrapper.find('.form-error').exists()).toBe(false)
  })

  it('should show error instead of hint when both provided', () => {
    const wrapper = mount(BaseInput, {
      props: { ...defaultProps, error: 'Required', hint: 'Enter email' }
    })

    expect(wrapper.find('.form-error').exists()).toBe(true)
    expect(wrapper.find('.form-hint').exists()).toBe(false)
  })

  it('should set aria-invalid when error exists', () => {
    const wrapper = mount(BaseInput, {
      props: { ...defaultProps, error: 'Invalid' }
    })

    expect(wrapper.find('input').attributes('aria-invalid')).toBe('true')
  })

  it('should set aria-describedby for error', () => {
    const wrapper = mount(BaseInput, {
      props: { ...defaultProps, error: 'Invalid' }
    })

    expect(wrapper.find('input').attributes('aria-describedby')).toBe('test-input-error')
  })

  it('should set aria-describedby for hint', () => {
    const wrapper = mount(BaseInput, {
      props: { ...defaultProps, hint: 'Help text' }
    })

    expect(wrapper.find('input').attributes('aria-describedby')).toBe('test-input-hint')
  })

  it('should apply has-error class on input when error exists', () => {
    const wrapper = mount(BaseInput, {
      props: { ...defaultProps, error: 'Error' }
    })

    expect(wrapper.find('input').classes()).toContain('has-error')
  })

  it('should be disabled when disabled prop is true', () => {
    const wrapper = mount(BaseInput, {
      props: { ...defaultProps, disabled: true }
    })

    expect(wrapper.find('input').attributes('disabled')).toBeDefined()
  })
})
