import type { CartItem } from "../context/CartContext";
import type { CartTotals } from "../lib/cartTotals";

export interface CheckoutAddress {
  name: string;
  email: string;
  phone: string;
  pincode: string;
  addressLine: string;
  city: string;
  state: string;
}

export interface ShippingMethod {
  id: "standard" | "express";
  label: string;
  description: string;
  fee: number;
  additionalDays: number;
}

export type PaymentMethod = "upi" | "card" | "netbanking" | "cod";

export interface PlacedOrder {
  id: string;
  createdAt: string;
  deliveryDate: string;
  address: CheckoutAddress;
  shippingMethod: ShippingMethod;
  paymentMethod: PaymentMethod;
  items: CartItem[];
  totals: CartTotals;
}
