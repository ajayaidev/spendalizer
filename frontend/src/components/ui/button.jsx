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
          "bg-gradient-to-r from-pink-600 to-purple-700 text-white shadow-md hover:from-pink-700 hover:to-purple-800 hover:shadow-lg",
        destructive:
          "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline:
          "border-2 border-purple-600 text-purple-700 shadow-sm hover:bg-gradient-to-r hover:from-pink-600 hover:to-purple-700 hover:text-white hover:border-transparent",
        secondary:
          "bg-gradient-to-r from-pink-200 to-purple-200 text-purple-800 shadow-sm hover:from-pink-300 hover:to-purple-300",
        ghost: "hover:bg-gradient-to-r hover:from-pink-50 hover:to-purple-50 hover:text-purple-700",
        link: "text-purple-600 underline-offset-4 hover:underline hover:text-pink-500",
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
