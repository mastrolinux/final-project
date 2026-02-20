/**
 * Unit tests for BaseSelect component.
 *
 * Tests verify label rendering, required asterisk, placeholder,
 * v-model emit, error/hint display, disabled state, and aria attributes.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BaseSelect from "@/components/common/BaseSelect.vue";

const defaultOptions = [
  { label: "English", value: "en" },
  { label: "Italian", value: "it" },
  { label: "Chinese", value: "zh", disabled: true },
];

describe("BaseSelect", () => {
  const mountSelect = (props: Record<string, unknown> = {}) =>
    mount(BaseSelect, {
      props: {
        id: "test-select",
        options: defaultOptions,
        modelValue: "",
        ...props,
      },
    });

  it("should render label when provided", () => {
    const wrapper = mountSelect({ label: "Language" });

    expect(wrapper.find("label").text()).toContain("Language");
    expect(wrapper.find("label").attributes("for")).toBe("test-select");
  });

  it("should not render label when not provided", () => {
    const wrapper = mountSelect();

    expect(wrapper.find("label").exists()).toBe(false);
  });

  it("should show required asterisk", () => {
    const wrapper = mountSelect({ label: "Language", required: true });

    expect(wrapper.find(".text-error").text()).toBe("*");
  });

  it("should render options from array", () => {
    const wrapper = mountSelect();

    const options = wrapper.findAll("option");
    expect(options).toHaveLength(3);
    expect(options[0].text()).toBe("English");
    expect(options[1].text()).toBe("Italian");
  });

  it("should render placeholder when provided", () => {
    const wrapper = mountSelect({ placeholder: "Choose..." });

    const options = wrapper.findAll("option");
    expect(options).toHaveLength(4); // placeholder + 3 options
    expect(options[0].text()).toBe("Choose...");
    expect(options[0].attributes("disabled")).toBeDefined();
  });

  it("should emit update:modelValue on change", async () => {
    const wrapper = mountSelect();

    await wrapper.find("select").setValue("it");

    const emitted = wrapper.emitted("update:modelValue");
    expect(emitted).toBeTruthy();
    expect(emitted![0][0]).toBe("it");
  });

  it("should display error message", () => {
    const wrapper = mountSelect({ error: "Required field" });

    expect(wrapper.find(".form-error").text()).toBe("Required field");
    expect(wrapper.find(".form-error").attributes("role")).toBe("alert");
  });

  it("should display hint when no error", () => {
    const wrapper = mountSelect({ hint: "Select your language" });

    expect(wrapper.find(".form-hint").text()).toBe("Select your language");
  });

  it("should not display hint when error is present", () => {
    const wrapper = mountSelect({ hint: "Select language", error: "Required" });

    expect(wrapper.find(".form-hint").exists()).toBe(false);
    expect(wrapper.find(".form-error").exists()).toBe(true);
  });

  it("should set aria-invalid when error exists", () => {
    const wrapper = mountSelect({ error: "Required" });

    expect(wrapper.find("select").attributes("aria-invalid")).toBe("true");
  });

  it("should apply has-error class when error exists", () => {
    const wrapper = mountSelect({ error: "Required" });

    expect(wrapper.find("select").classes()).toContain("has-error");
  });

  it("should set disabled attribute", () => {
    const wrapper = mountSelect({ disabled: true });

    expect(wrapper.find("select").attributes("disabled")).toBeDefined();
  });

  it("should disable individual options", () => {
    const wrapper = mountSelect();

    const options = wrapper.findAll("option");
    expect(options[2].attributes("disabled")).toBeDefined(); // zh is disabled
    expect(options[0].attributes("disabled")).toBeUndefined();
  });

  it("should set aria-describedby for hint", () => {
    const wrapper = mountSelect({ hint: "Help text" });

    expect(wrapper.find("select").attributes("aria-describedby")).toBe(
      "test-select-hint",
    );
  });

  it("should set aria-describedby for error", () => {
    const wrapper = mountSelect({ error: "Error text" });

    expect(wrapper.find("select").attributes("aria-describedby")).toBe(
      "test-select-error",
    );
  });
});
