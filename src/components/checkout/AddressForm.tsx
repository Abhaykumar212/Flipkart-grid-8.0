import { useState } from "react";
import { Button } from "../ui/Button";
import type { CheckoutAddress } from "../../types/checkout";

export type Address = CheckoutAddress;

export const EMPTY_ADDRESS: Address = {
  name: "",
  email: "",
  phone: "",
  pincode: "",
  addressLine: "",
  city: "",
  state: "",
};

export function isAddressComplete(address: Address): boolean {
  return (
    address.name.trim().length >= 2 &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address.email) &&
    /^\d{10}$/.test(address.phone) &&
    /^\d{6}$/.test(address.pincode) &&
    address.addressLine.trim().length >= 8 &&
    address.city.trim().length >= 2 &&
    address.state.trim().length >= 2
  );
}

interface AddressFormProps {
  value: Address;
  onChange: (next: Address) => void;
  onSubmit: () => void;
}

const fieldClass = "h-12 w-full rounded-[2px] border border-fk-border bg-white px-3 text-base text-fk-ink placeholder:text-fk-muted focus:border-fk-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-fk-blue";

export function AddressForm({ value, onChange, onSubmit }: AddressFormProps) {
  const [attempted, setAttempted] = useState(false);
  const set = (key: keyof Address) => (event: React.ChangeEvent<HTMLInputElement>) => {
    let next = event.target.value;
    if (key === "phone") next = next.replace(/\D/g, "").slice(0, 10);
    if (key === "pincode") next = next.replace(/\D/g, "").slice(0, 6);
    onChange({ ...value, [key]: next });
  };
  const complete = isAddressComplete(value);

  return (
    <form className="bg-white p-4 sm:p-6" data-testid="address-form" noValidate onSubmit={(event) => { event.preventDefault(); setAttempted(true); if (complete) onSubmit(); }}>
      <div className="mb-4">
        <h1 className="text-fk-lg font-medium uppercase tracking-wide text-fk-blue">Delivery Address</h1>
        <p className="mt-1 text-fk-sm text-fk-muted">Guest checkout · No account required</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="text-fk-sm font-medium text-fk-ink">Full name<input name="name" className={`${fieldClass} mt-1`} placeholder="Full name" autoComplete="name" required value={value.name} onChange={set("name")} /></label>
        <label className="text-fk-sm font-medium text-fk-ink">Email address<input name="email" type="email" spellCheck={false} className={`${fieldClass} mt-1`} placeholder="you@example.com" autoComplete="email" required value={value.email} onChange={set("email")} /></label>
        <label className="text-fk-sm font-medium text-fk-ink">Mobile number<input name="phone" type="tel" inputMode="numeric" className={`${fieldClass} mt-1`} placeholder="10-digit mobile number" autoComplete="tel" required value={value.phone} onChange={set("phone")} /></label>
        <label className="text-fk-sm font-medium text-fk-ink">Pincode<input name="pincode" inputMode="numeric" className={`${fieldClass} mt-1`} placeholder="6-digit pincode" autoComplete="postal-code" required value={value.pincode} onChange={set("pincode")} /></label>
        <label className="text-fk-sm font-medium text-fk-ink sm:col-span-2">Address<input name="street-address" className={`${fieldClass} mt-1`} placeholder="House number, area and street" autoComplete="street-address" required value={value.addressLine} onChange={set("addressLine")} /></label>
        <label className="text-fk-sm font-medium text-fk-ink">City<input name="city" className={`${fieldClass} mt-1`} placeholder="City" autoComplete="address-level2" required value={value.city} onChange={set("city")} /></label>
        <label className="text-fk-sm font-medium text-fk-ink">State<input name="state" className={`${fieldClass} mt-1`} placeholder="State" autoComplete="address-level1" required value={value.state} onChange={set("state")} /></label>
      </div>

      {attempted && !complete && <p className="mt-4 text-fk-base text-fk-flame" role="alert">Enter a valid email, 10-digit mobile number, 6-digit pincode, and complete address.</p>}
      <Button type="submit" variant="cart" className="mt-5 min-h-12 w-full sm:w-auto" data-testid="save-address-button">Save and Deliver Here</Button>
    </form>
  );
}
