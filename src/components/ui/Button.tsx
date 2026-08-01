import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "login" | "cart" | "buy" | "ghost" | "outline";
type Size = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-fk-blue text-white hover:bg-fk-blue-dark",
  login:
    "bg-white text-fk-blue border border-fk-blue/0 hover:shadow-sm",
  cart: "bg-fk-orange text-white hover:brightness-95",
  buy: "bg-fk-flame text-white hover:brightness-95",
  ghost: "bg-transparent text-fk-ink hover:bg-black/5",
  outline: "bg-white text-fk-blue border border-fk-blue hover:bg-fk-blue/5",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-3 py-1.5 text-fk-sm",
  md: "px-6 py-3 text-fk-md",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-[2px] font-medium uppercase tracking-[0.2px] transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
