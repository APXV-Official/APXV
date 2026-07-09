import * as React from "react";
import { cn } from "../lib/utils";

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: React.ReactNode;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, disabled, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id ?? generatedId;

    return (
      <label
        htmlFor={inputId}
        className={cn("apxv-checkbox shrink-0", className)}
      >
        <span className="apxv-checkbox-control" aria-hidden>
          <input
            type="checkbox"
            ref={ref}
            id={inputId}
            disabled={disabled}
            {...props}
          />
          <span className="apxv-checkbox-box">
            <svg
              viewBox="0 0 12 12"
              fill="none"
              className="apxv-checkbox-icon"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M2 6l3 3 5-5" />
            </svg>
          </span>
        </span>
        {label && <span className="apxv-checkbox-label">{label}</span>}
      </label>
    );
  },
);
Checkbox.displayName = "Checkbox";