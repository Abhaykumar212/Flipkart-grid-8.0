import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Gift, X, ArrowRight, CheckCircle2 } from 'lucide-react';
import { eventTimeline } from '../../lib/eventTimeline';

export const EmailCaptureModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const hasAsked = sessionStorage.getItem('fk-email-asked');
    if (!hasAsked) {
      const timer = setTimeout(() => {
        setIsOpen(true);
        sessionStorage.setItem('fk-email-asked', 'true');
        eventTimeline.record('email_modal_viewed', {});
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, []);

  const validateEmail = (email: string) => {
    return email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError('Email is required');
      return;
    }
    if (!validateEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }

    setError('');
    setIsSubmitting(true);

    try {
      const response = await fetch('http://localhost:8000/api/capture-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: eventTimeline.getSessionId(),
          email: email
        }),
      });

      if (response.ok) {
        sessionStorage.setItem('fk-user-email', email);
        eventTimeline.record('email_captured', { email });
        setIsSuccess(true);
        setTimeout(() => {
          setIsOpen(false);
        }, 2000);
      } else {
        setError('Something went wrong. Please try again.');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    eventTimeline.record('email_modal_dismissed', {});
    setIsOpen(false);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={handleSkip}
          />
          
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.5 }}
            className="relative w-full max-w-md overflow-hidden rounded-2xl bg-white shadow-2xl"
          >
            {/* Header / Gradient */}
            <div className="relative h-32 bg-gradient-to-r from-blue-600 to-blue-400 p-6 text-white overflow-hidden">
              <div className="absolute -right-4 -top-4 opacity-20">
                <Gift size={120} />
              </div>
              <button 
                onClick={handleSkip}
                className="absolute right-4 top-4 rounded-full bg-white/20 p-1 text-white hover:bg-white/30 transition-colors"
              >
                <X size={18} />
              </button>
              
              <div className="relative z-10 flex h-full flex-col justify-end">
                <div className="flex items-center gap-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/20 backdrop-blur-md">
                    <Gift size={20} className="text-white" />
                  </div>
                  <h3 className="text-xl font-bold tracking-tight">Unlock Exclusive Perks</h3>
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="p-6">
              {!isSuccess ? (
                <>
                  <p className="mb-6 text-sm text-gray-600">
                    Get exclusive deals, price drop alerts on your wishlist items, and personalized offers sent straight to your inbox.
                  </p>
                  
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="Enter your email address"
                        className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm text-gray-900 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                      />
                      {error && (
                        <p className="mt-1.5 text-xs text-red-500">{error}</p>
                      )}
                    </div>
                    
                    <div className="flex flex-col gap-2">
                      <button
                        type="submit"
                        disabled={isSubmitting}
                        className="group flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white transition-all hover:bg-blue-700 disabled:opacity-70"
                      >
                        {isSubmitting ? 'Submitting...' : 'Continue'}
                        {!isSubmitting && <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />}
                      </button>
                      
                      <button
                        type="button"
                        onClick={handleSkip}
                        className="text-center text-xs text-gray-500 hover:text-gray-700 transition-colors"
                      >
                        No thanks, I'll shop at regular prices
                      </button>
                    </div>
                  </form>
                </>
              ) : (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col items-center justify-center py-6 text-center"
                >
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 text-green-500">
                    <CheckCircle2 size={32} />
                  </div>
                  <h4 className="mb-2 text-lg font-semibold text-gray-900">You're on the list!</h4>
                  <p className="text-sm text-gray-500">Keep an eye on your inbox for upcoming deals.</p>
                </motion.div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
