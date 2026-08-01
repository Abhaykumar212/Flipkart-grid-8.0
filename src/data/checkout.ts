import { Banknote, CreditCard, Landmark, Smartphone, Truck, Zap, type LucideIcon } from "lucide-react";
import type { PaymentMethod, ShippingMethod } from "../types/checkout";

export const shippingMethods: ShippingMethod[] = [
  {
    id: "standard",
    label: "Standard Delivery",
    description: "Tracked delivery with free fulfilment on eligible orders",
    fee: 0,
    additionalDays: 0,
  },
  {
    id: "express",
    label: "Express Delivery",
    description: "Priority fulfilment and the earliest available delivery slot",
    fee: 99,
    additionalDays: -1,
  },
];

export const paymentMethods: {
  id: PaymentMethod;
  label: string;
  hint: string;
  icon: LucideIcon;
}[] = [
  { id: "upi", label: "UPI", hint: "Pay using any UPI app", icon: Smartphone },
  { id: "card", label: "Credit / Debit / ATM Card", hint: "Secure demo selection; no card details are collected", icon: CreditCard },
  { id: "netbanking", label: "Net Banking", hint: "Continue with your preferred bank", icon: Landmark },
  { id: "cod", label: "Cash on Delivery", hint: "Pay when your order arrives", icon: Banknote },
];

export const shippingIcons: Record<ShippingMethod["id"], LucideIcon> = {
  standard: Truck,
  express: Zap,
};

export const paymentMethodLabel = new Map(paymentMethods.map((method) => [method.id, method.label]));
