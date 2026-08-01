import { Button } from "../ui/Button";

export interface Address {
  name: string;
  phone: string;
  pincode: string;
  addressLine: string;
  city: string;
  state: string;
}

export const EMPTY_ADDRESS: Address = {
  name: "",
  phone: "",
  pincode: "",
  addressLine: "",
  city: "",
  state: "",
};

/** Every field is required — that's the only gate on advancing past step 1. */
export function isAddressComplete(address: Address): boolean {
  return Object.values(address).every((v) => v.trim().length > 0);
}

interface AddressFormProps {
  value: Address;
  onChange: (next: Address) => void;
  onSubmit: () => void;
}

const fieldClass =
  "h-10 w-full rounded-[2px] border border-fk-border bg-fk-bg px-3 text-fk-md text-fk-ink placeholder:text-fk-muted focus:border-fk-blue focus:bg-white focus:outline-none";

export function AddressForm({ value, onChange, onSubmit }: AddressFormProps) {
  const set = (key: keyof Address) => (e: React.ChangeEvent<HTMLInputElement>) =>
    onChange({ ...value, [key]: e.target.value });

  const complete = isAddressComplete(value);

  return (
    <form
      className="bg-white p-4 sm:p-6"
      data-testid="address-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (complete) onSubmit();
      }}
    >
      <h2 className="mb-4 text-fk-md font-medium uppercase tracking-wide text-fk-blue">
        Delivery Address
      </h2>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <input
          className={fieldClass}
          placeholder="Name"
          aria-label="Name"
          name="name"
          required
          value={value.name}
          onChange={set("name")}
        />
        <input
          className={fieldClass}
          placeholder="10-digit mobile number"
          aria-label="Phone"
          name="phone"
          required
          value={value.phone}
          onChange={set("phone")}
        />
        <input
          className={fieldClass}
          placeholder="Pincode"
          aria-label="Pincode"
          name="pincode"
          required
          value={value.pincode}
          onChange={set("pincode")}
        />
        <input
          className={fieldClass}
          placeholder="City"
          aria-label="City"
          name="city"
          required
          value={value.city}
          onChange={set("city")}
        />
        <input
          className={`${fieldClass} sm:col-span-2`}
          placeholder="Address (Area and Street)"
          aria-label="Address"
          name="addressLine"
          required
          value={value.addressLine}
          onChange={set("addressLine")}
        />
        <input
          className={fieldClass}
          placeholder="State"
          aria-label="State"
          name="state"
          required
          value={value.state}
          onChange={set("state")}
        />
      </div>

      <Button
        type="submit"
        variant="cart"
        className="mt-5"
        disabled={!complete}
        data-testid="save-address-button"
      >
        Save and Deliver Here
      </Button>
    </form>
  );
}
