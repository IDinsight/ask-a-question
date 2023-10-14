// CardPage.tsx
"use client";
import React, { useState } from "react";
import { PencilIcon, TrashIcon } from "@heroicons/react/20/solid";

type Card = {
  id: number;
  title: string;
  content: string;
  labels: string[];
  expanded: boolean;
};

const CardPage: React.FC = () => {
  const [cards, setCards] = useState<Card[]>([]);
  const [nextId, setNextId] = useState(1);

  const addCard = () => {
    const newCard: Card = {
      id: nextId,
      title: "New Card",
      content: "New Card Content",
      labels: [],
      expanded: false,
    };
    setCards([...cards, newCard]);
    setNextId(nextId + 1);
  };

  const deleteCard = (id: number) => {
    setCards(cards.filter((card) => card.id !== id));
  };

  const editCard = (id: number, content: string) => {
    const updatedCards = cards.map((card) =>
      card.id === id ? { ...card, content: content } : card
    );
    setCards(updatedCards);
  };

  const addLabel = (id: number, label: string) => {
    const updatedCards = cards.map((card) =>
      card.id === id ? { ...card, labels: [...card.labels, label] } : card
    );
    setCards(updatedCards);
  };
  const toggleExpand = (id: number) => {
    console.log("toggleExpand");
    setCards((prevCards) =>
      prevCards.map(
        (card) =>
          card.id === id
            ? { ...card, expanded: !card.expanded }
            : { ...card, expanded: false } // collapse all other cards
      )
    );
  };

  return (
    <div className="grid grid-cols-1 grid-flow-dense sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2 h-auto">
      {cards.map((card) => (
        <div
          key={card.id}
          className={`relative p-6 bg-white border border-gray-200 rounded-lg shadow dark:bg-gray-800 dark:border-gray-700 ${
            card.expanded ? "row-span-2 col-span-2" : ""
          }`}
          onClick={() => toggleExpand(card.id)}
        >
          {/* Icons Container */}
          <div className="absolute flex top-2 right-2 ">
            <PencilIcon
              className="w-5 h-5 text-gray-500 cursor-pointer hover:text-gray-700"
              onClick={() => editCard(card.id, "edited content")}
            />
            <TrashIcon
              className="w-5 h-5 text-red-500 cursor-pointer hover:text-red-700"
              onClick={() => deleteCard(card.id)}
            />
          </div>
          <a href="#">
            <h5 className="mb-2 text-2xl font-bold tracking-tight text-gray-900 dark:text-white">
              {card.title}
            </h5>
          </a>
          <p className="mb-3 font-normal text-gray-700 dark:text-gray-400">
            {card.content}
          </p>
          <a
            href="#"
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-center text-white bg-blue-700 rounded-lg hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
          >
            Details
            <svg
              className="w-3.5 h-3.5 ml-2"
              aria-hidden="true"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 14 10"
            >
              <path
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M1 5h12m0 0L9 1m4 4L9 9"
              />
            </svg>
          </a>
        </div>
      ))}
      <button className="add-card" onClick={addCard}>
        +
      </button>
    </div>
  );
};

export default CardPage;
