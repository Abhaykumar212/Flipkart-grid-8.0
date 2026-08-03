import { RatingStars } from '../ui/RatingStars';
import { ChevronRight } from 'lucide-react';

interface SellerInfoProps {
  seller: {
    name: string;
    rating: number;
  };
  delivery: {
    free: boolean;
    estimatedDays: number;
    express: boolean;
  };
}

export function SellerInfo({ seller, delivery }: SellerInfoProps) {
  return (
    <div className="border border-fk-border rounded-[2px] p-4 bg-white">
      <h3 className="text-fk-muted text-fk-sm font-medium mb-3 uppercase tracking-wider">Seller</h3>
      
      <div className="flex items-center gap-3 mb-4">
        <a href="#" className="text-fk-blue font-medium hover:underline text-fk-base">
          {seller.name}
        </a>
        <RatingStars value={seller.rating} variant="pill" size="sm" />
      </div>
      
      <ul className="space-y-2 mb-4 text-fk-sm text-fk-ink">
        <li className="flex items-start gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-fk-muted mt-1.5 shrink-0" />
          <span>7 Day Replacement Policy</span>
        </li>
        <li className="flex items-start gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-fk-muted mt-1.5 shrink-0" />
          <span>GST Invoice Available</span>
        </li>
        {delivery.free && (
          <li className="flex items-start gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-fk-muted mt-1.5 shrink-0" />
            <span className="text-fk-green font-medium">Free Delivery</span>
          </li>
        )}
        {delivery.express && (
          <li className="flex items-start gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-fk-muted mt-1.5 shrink-0" />
            <span className="font-medium">Express Delivery Available</span>
          </li>
        )}
      </ul>
      
      <a href="#" className="text-fk-blue text-fk-sm font-medium flex items-center hover:underline">
        View all sellers
        <ChevronRight className="w-3 h-3 ml-1" />
      </a>
    </div>
  );
}
