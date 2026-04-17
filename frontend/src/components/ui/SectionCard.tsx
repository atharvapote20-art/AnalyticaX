import type { ReactNode } from "react";
import { motion } from "framer-motion";

type SectionCardProps = {
  children: ReactNode;
  className?: string;
};

export function SectionCard({ children, className }: SectionCardProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`card glass ${className ?? ""}`.trim()}
    >
      {children}
    </motion.section>
  );
}
