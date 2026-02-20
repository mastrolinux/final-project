<script setup lang="ts">
/**
 * Reusable avatar display component.
 *
 * Encapsulates the fallback chain: image URL -> text initials.
 * Renders an <img> when `src` is truthy, otherwise renders a <div>
 * with computed initials derived from the `name` prop.
 */
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    /** Avatar image URL (null falls back to initials). */
    src?: string | null;
    /** Display name used to derive initials for the fallback. */
    name?: string;
    /** Size variant matching the existing .avatar CSS classes. */
    size?: "sm" | "md" | "lg" | "xl";
  }>(),
  {
    src: null,
    name: "",
    size: "md",
  },
);

const initials = computed(() => {
  const n = props.name || "U";
  return n
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
});

const sizeClass = computed(() => {
  switch (props.size) {
    case "sm":
      return "avatar-display-sm";
    case "lg":
      return "avatar-display-lg";
    case "xl":
      return "avatar-display-xl";
    default:
      return "avatar-display-md";
  }
});
</script>

<template>
  <div class="avatar-display" :class="sizeClass">
    <img
      v-if="src"
      :src="src"
      :alt="name ? `${name} avatar` : 'Avatar'"
      class="avatar-display-img"
    />
    <span v-else class="avatar-display-initials">{{ initials }}</span>
  </div>
</template>

<style scoped>
.avatar-display {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  background-color: var(--color-primary-100);
  color: var(--color-primary-700);
  font-weight: var(--font-weight-medium);
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-display-sm {
  width: 2rem;
  height: 2rem;
  font-size: var(--font-size-xs);
}

.avatar-display-md {
  width: 2.5rem;
  height: 2.5rem;
  font-size: var(--font-size-sm);
}

.avatar-display-lg {
  width: 3rem;
  height: 3rem;
  font-size: var(--font-size-base);
}

.avatar-display-xl {
  width: 5rem;
  height: 5rem;
  font-size: 2rem;
  font-weight: var(--font-weight-semibold);
}

.avatar-display-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-display-initials {
  line-height: 1;
  user-select: none;
}
</style>
