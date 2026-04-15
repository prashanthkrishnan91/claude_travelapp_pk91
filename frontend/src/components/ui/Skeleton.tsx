import clsx from "clsx";

type SkeletonVariant = "text" | "avatar" | "badge" | "button" | "card";

interface SkeletonProps {
  className?: string;
  variant?: SkeletonVariant;
}

const VARIANT_CLASSES: Record<SkeletonVariant, string> = {
  text:   "h-4 rounded",
  avatar: "rounded-full",
  badge:  "h-5 w-16 rounded-full",
  button: "h-9 rounded-xl",
  card:   "h-32 rounded-xl",
};

export function Skeleton({ className, variant }: SkeletonProps) {
  return (
    <div
      className={clsx("skeleton", variant && VARIANT_CLASSES[variant], className)}
      aria-hidden="true"
    />
  );
}
