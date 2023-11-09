"use client";

import React, { useState, useEffect } from "react";
import { ContentCard, Content } from "../components/ContentCard";
import { NavBar } from "../components/NavBar";
import { jwtDecode } from "jwt-decode";
import { XMarkIcon } from "@heroicons/react/20/solid";

const backendUrl: string = process.env.BACKEND_URL || "http://localhost:8000";

export default function Home() {
  const [cards, setCards] = useState<Content[]>([]);
  const [showEditModal, setShowEditModal] = useState(false);
  const [cardToEdit, setCardToEdit] = useState<Content | null>(null);
  const [newCardText, setNewCardText] = useState("");

  const deleteCard = (id: string) => {
    fetch(`${backendUrl}/content/${id}/delete`, {
      method: "DELETE",
      headers: get_api_headers(),
    }).then((response) => {
      if (response.ok) {
        setCards(cards.filter((card: Content) => card.content_id !== id));
      } else {
        throw new Error("Could not delete " + id);
      }
    });
  };

  const get_api_headers = () => {
    const headers = {};
    const tokenString = localStorage.getItem("token");

    if (tokenString) {
      const token = JSON.parse(tokenString);
      const decodedAccessToken = jwtDecode(token.access_token);
      const isTokenValid = decodedAccessToken.exp * 1000 > Date.now();
      if (isTokenValid) {
        headers["Authorization"] = `Bearer ${token.access_token}`;
        headers["Content-Type"] = "application/json";
      } else {
        console.log("Access token expired");
        window.location.href = "/login";
      }
      return headers;
    } else {
      console.log("No token found");
      window.location.href = "/login";
    }
  };

  const isFullAccess = (): boolean => {
    if (typeof window !== "undefined") {
      const tokenString = localStorage.getItem("token");
      if (tokenString) {
        const token = JSON.parse(tokenString);
        const decodedAccessToken = jwtDecode(token.access_token);
        const isTokenValid = decodedAccessToken.exp * 1000 > Date.now();
        return isTokenValid && token.access_level == "fullaccess"
          ? true
          : false;
      } else {
        window.location.href = "/login";
      }
    } else {
      return false;
    }
  };

  const saveEditedCard = (card: Content) => {
    fetch(`${backendUrl}/content/${card.content_id}/edit`, {
      method: "PUT",
      headers: get_api_headers(),
      body: JSON.stringify(card),
    }).then((response) => {
      if (response.ok) {
        console.log("updated card: " + card.content_id);
        setCards(
          cards.map((c: Content) => {
            if (c.content_id === card.content_id) {
              return card;
            } else {
              return c;
            }
          }),
        );
      } else {
        throw new Error("Could not save " + card.content_id);
      }
    });
  };

  const saveNewCard = (content_text: string) => {
    fetch(`${backendUrl}/content/create`, {
      method: "POST",
      headers: get_api_headers(),
      body: JSON.stringify({ content_text: content_text }),
    })
      .then((response) => {
        if (response.ok) {
          return response.json();
        } else {
          throw new Error("Could not save new card");
        }
      })
      .then((data) => {
        setCards([...cards, data]);
      });
  };

  const editCard = (card: Content) => {
    setCardToEdit(card);
    setShowEditModal(true);
  };

  const addCard = () => {
    setCardToEdit(null);
    setShowEditModal(true);
  };

  useEffect(() => {
    fetch(`${backendUrl}/content/list`, {
      headers: get_api_headers(),
    })
      .then((response) => {
        if (response.ok) {
          let resp = response.json();
          return resp;
        } else {
          throw new Error("Something went wrong ...");
        }
      })
      .then((data) => {
        setCards(data);
      })
      .catch((error) => console.log(error));
  }, []);

  const showCardEditButtons = isFullAccess();

  return (
    <>
      <NavBar />
      <main className="flex-wrap items-center justify-between ">
        <div className="m-5">
          <div className="grid grid-cols-1 justify-center sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
            {/* create a card for each object */}
            {cards.map((card: Content) => (
              <ContentCard
                key={card.content_id}
                content_id={card.content_id}
                content_text={card.content_text}
                deleteMe={deleteCard}
                editMe={editCard}
                expanded={false}
                showEditButton={showCardEditButtons}
              />
            ))}
            {showCardEditButtons ? (
              <button
                className="add-card min-h-[10rem] outline-dashed rounded outline-gray-700"
                onClick={addCard}
              >
                +
              </button>
            ) : null}
          </div>
        </div>

        {showEditModal ? (
          <>
            <div className="flex backdrop-blur justify-center items-center overflow-x-hidden overflow-y-auto fixed inset-0 z-50 outline-none focus:outline-none">
              <div className="relative w-auto my-6 mx-auto max-w-3xl">
                <div className="border-0 rounded-lg shadow-lg relative flex flex-col w-full bg-gray-700 outline-none focus:outline-none">
                  <div className="flex items-start justify-between p-5 rounded-t ">
                    <h3 className="text-xl">
                      {cardToEdit ? (
                        <>
                          Edit Content
                          <div className="text-xs text-gray-400">
                            id: {cardToEdit.content_id}
                          </div>
                        </>
                      ) : (
                        "New Content"
                      )}
                    </h3>
                    <XMarkIcon
                      className="w-4 h-4 float-right"
                      onClick={() => setShowEditModal(false)}
                    />
                  </div>
                  <div className="relative p-2 flex flex-auto">
                    <textarea
                      id="content_text"
                      rows={16}
                      cols={50}
                      className="shadow appearance-none border active:outline-none border-neutral-400 text-sm rounded w-full bg-gray-800 py-4 px-4 text-gray-400"
                      defaultValue={cardToEdit?.content_text}
                      placeholder="Enter content text"
                      onChange={(e: React.FormEvent<HTMLTextAreaElement>) => {
                        const target = e.target as HTMLTextAreaElement;
                        cardToEdit
                          ? setCardToEdit(() => {
                              cardToEdit!.content_text = target.value;
                              return cardToEdit;
                            })
                          : setNewCardText(target.value);
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-end pb-4 px-4 rounded-b">
                    <button
                      id="closeButton"
                      className="text-red-500 background-transparent font-bold uppercase px-6 py-2 text-sm outline-none focus:outline-none mr-1 mb-1"
                      type="button"
                      onClick={() => setShowEditModal(false)}
                    >
                      Close
                    </button>
                    <button
                      id="submitButton"
                      className="text-white bg-blue-500 active:bg-blue-700 font-bold uppercase text-sm px-6 py-3 rounded shadow hover:shadow-lg outline-none focus:outline-none mr-1 mb-1"
                      type="button"
                      onClick={() => {
                        cardToEdit
                          ? saveEditedCard(cardToEdit!)
                          : saveNewCard(newCardText);
                        setShowEditModal(false);
                      }}
                    >
                      Submit
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </main>
    </>
  );
}
