<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    variant?: "text" | "avatar" | "card" | "button" | "heading";
    width?: string;
    height?: string;
    rounded?: boolean;
  }>(),
  {
    variant: "text",
    rounded: false,
  },
);

const customStyle = computed(() => {
  const style: Record<string, string> = {};
  if (props.width) style.width = props.width;
  if (props.height) style.height = props.height;
  return style;
});

const classes = computed(() => [
  "skeleton",
  `skeleton-${props.variant}`,
  { "skeleton-rounded": props.rounded },
]);
</script>

<template>
  <div :class="classes" :style="customStyle" aria-hidden="true" />
</template>

<style scoped>
.skeleton {
  background: linear-gradient(
    90deg,
    var(--color-gray-200) 25%,
    var(--color-gray-100) 50%,
    var(--color-gray-200) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Variants */
.skeleton-text {
  height: 1rem;
  width: 100%;
}

.skeleton-heading {
  height: 1.5rem;
  width: 60%;
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.skeleton-card {
  height: 120px;
  width: 100%;
}

.skeleton-button {
  height: 40px;
  width: 100px;
}

.skeleton-rounded {
  border-radius: var(--radius-full);
}

/* Dark mode support */
:global(.dark) .skeleton {
  background: linear-gradient(
    90deg,
    var(--color-gray-700) 25%,
    var(--color-gray-600) 50%,
    var(--color-gray-700) 75%
  );
  background-size: 200% 100%;
}

/* Respect reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
    background: var(--color-gray-200);
  }

  :global(.dark) .skeleton {
    background: var(--color-gray-700);
  }
}
</style>
