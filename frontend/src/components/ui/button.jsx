import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-to-r from-fuchsia-600 to-violet-800 text-white shadow-md hover:from-fuchsia-700 hover:to-violet-900 hover:shadow-lg",
        destructive:
          "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline:
          "border-2 border-violet-600 text-violet-700 shadow-sm hover:bg-gradient-to-r hover:from-fuchsia-600 hover:to-violet-800 hover:text-white hover:border-transparent",
        secondary:
          "bg-gradient-to-r from-fuchsia-200 to-violet-200 text-violet-900 shadow-sm hover:from-fuchsia-300 hover:to-violet-300",
        ghost: "hover:bg-gradient-to-r hover:from-violet-50 hover:to-purple-100 hover:text-purple-800",
        link: "text-violet-700 underline-offset-4 hover:underline hover:text-purple-800",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const Button = React.forwardRef(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button"
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      {...props} />
  );
})
Button.displayName = "Button"

export { Button, buttonVariants }
