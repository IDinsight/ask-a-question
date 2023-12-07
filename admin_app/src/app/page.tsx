"use client";

import React, { useState, useEffect } from "react";
import { ContentCard, Content } from "../components/ContentCard";
import { ConfirmDelete, EditModal } from "../components/ContentModals";
import { SearchBar } from "../components/SearchBar";
import { backendUrl } from "../components/Config";
import { getAccessLevel, AccessLevel, AccessToken } from "../utils/auth";
import { useRouter, usePathname } from "next/navigation";

export default function Home() {
  const [cards, setCards] = useState<Content[]>([]);
  const [filteredCards, setFilteredCards] = useState<Content[]>([]);
  const [cardToEdit, setCardToEdit] = useState<Content | null>(null);
  const [newCardText, setNewCardText] = useState("");
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirmModal, setShowDeleteConfirmModal] = useState(false);
  const [cardToDelete, setCardToDelete] = useState<Content | null>(null);

  const [accessToken, setAccessToken] = useState<AccessToken | null>(null);
  const [accessLevel, setAccessLevel] = useState<AccessLevel | null>(null);

  const router = useRouter();
  const pathname = usePathname();

  const get_api_headers = (token: AccessToken) => {
    const headers: { [key: string]: string } = {};

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
      headers["Content-Type"] = "application/json";
      return headers;
    } else {
      throw Error("No token found");
    }
  };

  const saveEditedCardInBackend = (card: Content) => {
    fetch(`${backendUrl}/content/${card.content_id}/edit`, {
      method: "PUT",
      headers: get_api_headers(accessToken),
      body: JSON.stringify(card),
    }).then((response) => {
      if (response.ok) {
        console.log("updated card: " + card.content_id);
        const newCardList = cards.map((c: Content) => {
          if (c.content_id === card.content_id) {
            return card;
          } else {
            return c;
          }
        });
        setCards(newCardList);
        setFilteredCards(newCardList);
      } else {
        throw new Error("Could not save " + card.content_id);
      }
    });
  };

  const saveNewCardInBackend = (content_text: string) => {
    fetch(`${backendUrl}/content/create`, {
      method: "POST",
      headers: get_api_headers(accessToken),
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
        setFilteredCards([...cards, data]);
      });
  };

  const deleteCardInBackend = (id: string) => {
    fetch(`${backendUrl}/content/${id}/delete`, {
      method: "DELETE",
      headers: get_api_headers(accessToken),
    }).then((response) => {
      if (response.ok) {
        const newCardList = cards.filter(
          (card: Content) => card.content_id !== id,
        );
        setCards(newCardList);
        setFilteredCards(newCardList);
      } else {
        throw new Error("Could not delete " + id);
      }
    });
  };

  // functions to edit and add content
  const editCard = (card: Content) => {
    setCardToEdit(card);
    setShowEditModal(true);
  };

  const addCard = () => {
    setCardToEdit(null);
    setShowEditModal(true);
  };

  const onContentChange = (content_text: string) => {
    cardToEdit
      ? setCardToEdit(() => {
          cardToEdit.content_text = content_text;
          return cardToEdit;
        })
      : setNewCardText(content_text);
  };

  const onChangeSubmit = () => {
    cardToEdit
      ? saveEditedCardInBackend(cardToEdit!)
      : saveNewCardInBackend(newCardText);
    setShowEditModal(false);
  };

  // functions to delete content
  const deleteCard = (card: Content) => {
    setCardToDelete(card);
    setShowDeleteConfirmModal(true);
  };

  const closeConfirmModal = () => {
    setShowDeleteConfirmModal(false);
    setCardToDelete(null);
  };

  const confirmDelete = (card: Content) => {
    deleteCardInBackend(card.content_id);
    setCardToDelete(null);
    closeConfirmModal();
  };

  useEffect(() => {
    const [isAuthenticated, access_level, access_token]: [
      boolean | null,
      AccessLevel,
      AccessToken,
    ] = getAccessLevel();

    setAccessToken(access_token);
    setAccessLevel(access_level);

    if (!isAuthenticated) {
      router.push("/login?fromPage=" + encodeURIComponent(pathname));
    }
    fetch(`${backendUrl}/content/list`, {
      headers: get_api_headers(access_token),
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
        setFilteredCards(data);
      })
      .catch((error) => console.log(error));
  }, [router, pathname]);

  const filterCards = (e: React.FormEvent<HTMLInputElement>) => {
    const searchTerm = e.currentTarget.value.toLowerCase();
    const filteredCards = cards.filter((card: Content) => {
      return card.content_text.toLowerCase().includes(searchTerm);
    });
    setFilteredCards(filteredCards);
  };

  const showCardEditButtons = accessLevel === "fullaccess";

  return (
    <div className="flex-grow">
      <div className="sticky top-0 z-10 justify-left w-full -px-4 items-center bg-blue-600 dark:bg-blue-900">
        <SearchBar onChange={filterCards} />
      </div>

      <main className="flex-grow overflow-y-auto items-center justify-between ">
        <div className="m-5">
          <div className="grid grid-cols-1 justify-center sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
            {/* create a card for each object */}
            {filteredCards.map((card: Content) => (
              <ContentCard
                key={card.content_id}
                content={card}
                editMe={editCard}
                showEditButton={showCardEditButtons}
                deleteMe={deleteCard}
              />
            ))}
            {showCardEditButtons ? (
              <button
                className="add-card min-h-[10rem] outline-dashed rounded dark:outline-gray-700 outline-gray-400"
                onClick={addCard}
              >
                +
              </button>
            ) : null}
          </div>
        </div>

        {showDeleteConfirmModal && cardToDelete && (
          <ConfirmDelete
            cardToDelete={cardToDelete}
            onDeleteConfirm={confirmDelete}
            onClose={closeConfirmModal}
            title={"Are you sure you want to delete this content?"}
          />
        )}

        {showEditModal && (
          <EditModal
            cardToEdit={cardToEdit}
            onChange={onContentChange}
            onSubmit={onChangeSubmit}
            onClose={() => setShowEditModal(false)}
          />
        )}
      </main>
    </div>
  );
}
