import { useState } from "react";
import { ThumbsUp } from "lucide-react";
import { Button } from "../ui/Button";

interface QnA {
  id: string;
  question: string;
  answer: string;
  helpfulCount: number;
}

const MOCK_QNA_BY_CATEGORY: Record<string, QnA[]> = {
  mobile: [
    { id: "1", question: "How is the battery life?", answer: "The battery easily lasts a full day with moderate usage. With heavy gaming, you might need to charge it in the evening.", helpfulCount: 45 },
    { id: "2", question: "Is the camera quality good for night photography?", answer: "Yes, the night mode works exceptionally well, reducing noise and capturing details.", helpfulCount: 32 },
    { id: "3", question: "Does it come with a charger in the box?", answer: "No, the charger is not included in the box. You will only get a Type-C cable.", helpfulCount: 112 },
    { id: "4", question: "Is this phone waterproof?", answer: "It has an IP68 rating, which means it is water and dust resistant.", helpfulCount: 28 },
    { id: "5", question: "How many software updates will it receive?", answer: "The brand promises 3 years of major OS updates and 4 years of security patches.", helpfulCount: 19 },
  ],
  electronics: [
    { id: "6", question: "What is the warranty period?", answer: "It comes with a standard 1-year manufacturer warranty.", helpfulCount: 24 },
    { id: "7", question: "Does it support HDMI 2.1?", answer: "Yes, it supports HDMI 2.1 for high refresh rate gaming.", helpfulCount: 15 },
    { id: "8", question: "What is the power consumption?", answer: "It consumes around 60W under normal operation.", helpfulCount: 9 },
    { id: "9", question: "Can it connect to Wi-Fi 6?", answer: "Yes, it has built-in support for Wi-Fi 6.", helpfulCount: 12 },
  ],
  audio: [
    { id: "10", question: "Is the noise cancellation effective in flights?", answer: "Yes, the Active Noise Cancellation (ANC) works really well in blocking out airplane engine noise.", helpfulCount: 56 },
    { id: "11", question: "Can I connect it to two devices simultaneously?", answer: "Yes, it supports multipoint connectivity, allowing you to connect to your phone and laptop at the same time.", helpfulCount: 41 },
    { id: "12", question: "How is the battery life?", answer: "You get around 30 hours of playback with ANC on.", helpfulCount: 22 },
    { id: "13", question: "Are they comfortable for long sessions?", answer: "The ear cushions are soft memory foam, making them very comfortable for extended use.", helpfulCount: 34 },
  ],
  appliance: [
    { id: "14", question: "Does Flipkart provide free installation?", answer: "Yes, free installation is provided by the brand within 48 hours of delivery.", helpfulCount: 88 },
    { id: "15", question: "What is the energy star rating?", answer: "This is a 5-star rated appliance, making it highly energy efficient.", helpfulCount: 45 },
    { id: "16", question: "Is the compressor inverter based?", answer: "Yes, it features an inverter compressor for better efficiency and less noise.", helpfulCount: 29 },
    { id: "17", question: "What is the warranty on the motor?", answer: "It comes with a 10-year warranty on the motor and 1 year comprehensive.", helpfulCount: 67 },
  ],
  fashion: [
    { id: "18", question: "Is the material pure cotton?", answer: "Yes, it is made of 100% premium cotton.", helpfulCount: 14 },
    { id: "19", question: "What are the wash care instructions?", answer: "Machine wash cold with like colors. Do not bleach. Tumble dry low.", helpfulCount: 9 },
    { id: "20", question: "Is the size chart accurate?", answer: "Yes, the fitting is true to size. Please refer to the size chart for exact measurements.", helpfulCount: 21 },
    { id: "21", question: "What is the return policy?", answer: "You can return it within 14 days of delivery if the tags are intact.", helpfulCount: 33 },
  ],
  default: [
    { id: "22", question: "Is this a genuine product?", answer: "Yes, all products sold by this seller are 100% genuine and come with a brand warranty.", helpfulCount: 156 },
    { id: "23", question: "What is the return policy?", answer: "This product has a 7-day replacement policy in case of defects.", helpfulCount: 89 },
    { id: "24", question: "Can I get a GST invoice for this?", answer: "Yes, you can enter your GST details during checkout to receive a GST invoice.", helpfulCount: 45 },
    { id: "25", question: "How long will delivery take?", answer: "Delivery usually takes 2-4 business days depending on your pin code.", helpfulCount: 112 },
  ]
};

export function QuestionsAndAnswers({
  productTitle,
  brand,
  category
}: {
  productTitle: string;
  brand: string;
  category: string;
}) {
  const [questionText, setQuestionText] = useState("");

  const normalizedCategory = category.toLowerCase();
  let categoryKey = "default";
  if (normalizedCategory.includes("mobile") || normalizedCategory.includes("phone")) categoryKey = "mobile";
  else if (normalizedCategory.includes("laptop") || normalizedCategory.includes("electronic") || normalizedCategory.includes("tv")) categoryKey = "electronics";
  else if (normalizedCategory.includes("audio") || normalizedCategory.includes("headphone") || normalizedCategory.includes("earphone")) categoryKey = "audio";
  else if (normalizedCategory.includes("appliance") || normalizedCategory.includes("fridge") || normalizedCategory.includes("washer")) categoryKey = "appliance";
  else if (normalizedCategory.includes("fashion") || normalizedCategory.includes("clothing") || normalizedCategory.includes("shoe")) categoryKey = "fashion";

  const qnaList = MOCK_QNA_BY_CATEGORY[categoryKey] || MOCK_QNA_BY_CATEGORY["default"];

  return (
    <div className="bg-white rounded-[2px] p-6 shadow-fk-card">
      <div className="flex items-center gap-3 mb-6">
        <h2 className="text-fk-xl font-medium">Questions & Answers</h2>
        <span className="bg-fk-muted/10 text-fk-muted text-fk-sm px-2 py-1 rounded-[2px]">
          {qnaList.length}
        </span>
      </div>

      <div className="space-y-6">
        {qnaList.map((qna) => (
          <div key={qna.id} className="pb-6 border-b border-fk-border last:border-0 last:pb-0">
            <div className="flex gap-2">
              <span className="text-fk-md font-medium text-fk-blue">Q:</span>
              <p className="text-fk-md font-medium text-fk-ink">{qna.question}</p>
            </div>
            <div className="flex gap-2 mt-2">
              <span className="text-fk-base font-medium text-fk-muted">A:</span>
              <div>
                <p className="text-fk-base text-fk-ink">{qna.answer}</p>
                <div className="flex items-center gap-4 mt-3">
                  <span className="text-fk-sm text-fk-muted flex items-center gap-1">
                    Anonymous
                  </span>
                  <div className="flex items-center gap-1 text-fk-sm text-fk-muted cursor-pointer hover:text-fk-blue">
                    <ThumbsUp className="w-4 h-4" />
                    <span>{qna.helpfulCount}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 pt-6 border-t border-fk-border">
        <h3 className="text-fk-base font-medium mb-3">Do you have a question?</h3>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Type your question here..."
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            className="flex-1 border border-fk-border rounded-[2px] px-4 py-2 text-fk-base focus:outline-none focus:border-fk-blue"
          />
          <Button 
            className="bg-fk-blue text-white hover:bg-fk-blue/90 px-8 rounded-[2px]"
            onClick={() => setQuestionText("")}
          >
            Submit
          </Button>
        </div>
      </div>
    </div>
  );
}
