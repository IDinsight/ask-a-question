// CardPage.tsx
"use client";
import React, { useState } from "react";

type Card = {
  id: number;
  content: string;
  labels: string[];
};

const CardPage: React.FC = () => {
  const [cards, setCards] = useState<Card[]>([]);
  const [nextId, setNextId] = useState(1);

  const addCard = () => {
    const newCard: Card = {
      id: nextId,
      content: "",
      labels: [],
    };
    setCards([...cards, newCard]);
    setNextId(nextId + 1);
  };

  const deleteCard = (id: number) => {
    setCards(cards.filter((card) => card.id !== id));
  };

  const editCard = (id: number, content: string) => {
    const updatedCards = cards.map((card) =>
      card.id === id ? { ...card, content } : card
    );
    setCards(updatedCards);
  };

  const addLabel = (id: number, label: string) => {
    const updatedCards = cards.map((card) =>
      card.id === id ? { ...card, labels: [...card.labels, label] } : card
    );
    setCards(updatedCards);
  };

  return (
    <div className="card-page ">
      {cards.map((card) => (
        <div
          key={card.id}
          className="flex-auto w-64 p-6 bg-white border border-gray-200 rounded-lg shadow dark:bg-gray-800 dark:border-gray-700"
        >
          <a href="#">
            <h5 className="mb-2 text-2xl font-bold tracking-tight text-gray-900 dark:text-white">
              Content title
            </h5>
          </a>
          <p className="mb-3 font-normal text-gray-700 dark:text-gray-400">
            Content text
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
