import { motion } from 'framer-motion';

interface StockUrgencyProps {
  inStock: boolean;
  quantityLeft: number;
}

export function StockUrgency({ inStock, quantityLeft }: StockUrgencyProps) {
  if (!inStock) {
    return (
      <div className="bg-white border border-fk-border p-4 rounded-[2px] mb-4">
        <h3 className="text-fk-flame text-fk-lg font-medium">Currently Unavailable</h3>
        <p className="text-fk-sm text-fk-muted mt-1">This item is out of stock</p>
        <button className="mt-4 px-6 py-2 border border-fk-blue text-fk-blue font-medium rounded-[2px] hover:bg-blue-50 transition-colors">
          Notify Me
        </button>
      </div>
    );
  }

  if (quantityLeft <= 5) {
    return (
      <div className="flex items-center gap-2 mb-4">
        <motion.div 
          className="w-2.5 h-2.5 rounded-full bg-amber-500"
          animate={{ opacity: [1, 0.5, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
        <span className="text-amber-600 font-bold text-fk-base">
          Hurry, Only {quantityLeft} left!
        </span>
      </div>
    );
  }

  if (quantityLeft <= 10) {
    return (
      <div className="mb-4">
        <span className="text-fk-flame font-medium text-fk-base">
          Only {quantityLeft} left in stock — order soon
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="w-2.5 h-2.5 rounded-full bg-fk-green" />
      <span className="text-fk-green font-medium text-fk-base">
        In Stock
      </span>
    </div>
  );
}
