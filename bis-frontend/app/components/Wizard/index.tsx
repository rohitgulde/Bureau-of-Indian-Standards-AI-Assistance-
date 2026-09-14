"use client";

import { Check, Circle } from "lucide-react";
import { WizardStep } from "../../lib/types";

interface WizardProps {
  steps: WizardStep[];
  currentStep: number;
  onStepClick?: (index: number) => void;
  children?: React.ReactNode;
}

export default function Wizard({ steps, currentStep, onStepClick, children }: WizardProps) {
  return (
    <div className="space-y-8">
      {/* Step indicator */}
      <div className="flex items-center">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center flex-1 last:flex-none">
            <button
              onClick={() => onStepClick?.(index)}
              disabled={index > currentStep}
              className="flex flex-col items-center gap-1.5 group disabled:cursor-not-allowed"
            >
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center border-2 transition-all ${
                  step.completed
                    ? "bg-gov-navy border-gov-navy text-white"
                    : index === currentStep
                    ? "border-gov-navy text-gov-navy bg-white scale-110 shadow-md"
                    : "border-border text-muted-foreground"
                }`}
              >
                {step.completed ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <span className="text-xs font-semibold">{index + 1}</span>
                )}
              </div>
              <span
                className={`text-xs font-medium hidden sm:block ${
                  index === currentStep ? "text-gov-navy" : "text-muted-foreground"
                }`}
              >
                {step.title}
              </span>
            </button>

            {index < steps.length - 1 && (
              <div
                className={`flex-1 h-0.5 mx-2 transition-colors ${
                  steps[index].completed ? "bg-gov-navy" : "bg-border"
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Current step info */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-base font-semibold text-foreground">
          {steps[currentStep]?.title}
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          {steps[currentStep]?.description}
        </p>
      </div>

      {/* Step content */}
      <div>{children}</div>
    </div>
  );
}