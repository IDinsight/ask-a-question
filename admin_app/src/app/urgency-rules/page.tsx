"use client";
import { useState } from "react";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Checkbox from "@mui/material/Checkbox";
import IconButton from "@mui/material/IconButton";
import CommentIcon from "@mui/icons-material/Comment";
import { Layout } from "@/components/Layout";
import { sizes } from "@/utils";
import { Delete, Edit } from "@mui/icons-material";
import { TextField } from "@mui/material";
import { Typography } from "@mui/material";
const UrgencyRulesPage = () => {
  const [checked, setChecked] = useState<number[]>([]);

  const [editableIndex, setEditableIndex] = useState(-1);
  const [items, setItems] = useState([
    "text1",
    "text2",
    "text3",
    "text4",
    "text5",
    "text6",
    "text7",
    "text8",
    "text9",
    "text10",
  ]);

  const handleToggle = (index: number) => () => {
    const currentIndex = checked.indexOf(index);
    const newChecked = [...checked];

    if (currentIndex === -1) {
      newChecked.push(index);
    } else {
      newChecked.splice(currentIndex, 1);
    }

    setChecked(newChecked);
  };
  const handleDoubleClick = (index: number) => () => {
    setEditableIndex(index);
  };

  const handleTextChange = (text: string, index: number) => {
    const newItems = [...items];
    newItems[index] = text;
    setItems(newItems);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setEditableIndex(-1);
    }
  };
  return (
    <Layout.FlexBox
      alignItems="center"
      gap={sizes.baseGap}
      py={5}
      bgcolor="white"
    >
      <Typography variant="h4" align="left">
        Urgency Rules
      </Typography>
      <List sx={{ width: "100%", maxWidth: "md", bgcolor: "background.paper" }}>
        {items.map((value: string, index: number) => {
          const labelId = `checkbox-list-label-${value}`;

          return (
            <ListItem
              key={index}
              sx={{ borderBottom: 1, borderColor: "divider" }}
              secondaryAction={
                <>
                  <IconButton edge="end" aria-label="delete" sx={{ mx: 0.5 }}>
                    <Delete fontSize="small" color="secondary" />
                  </IconButton>
                  <IconButton aria-label="edit">
                    <Edit fontSize="small" color="secondary" />
                  </IconButton>
                </>
              }
              disablePadding
              onDoubleClick={handleDoubleClick(index)}
            >
              <ListItemButton
                role={undefined}
                onClick={handleToggle(index)}
                dense
              >
                <ListItemIcon>
                  <Checkbox
                    edge="start"
                    checked={checked.indexOf(index) !== -1}
                    tabIndex={-1}
                    disableRipple
                    inputProps={{ "aria-labelledby": labelId }}
                  />
                </ListItemIcon>
                {editableIndex === index ? (
                  <TextField
                    fullWidth
                    value={value}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      handleTextChange(e.target.value, index)
                    }
                    onKeyDown={handleKeyDown}
                    onBlur={() => setEditableIndex(-1)}
                  />
                ) : (
                  <ListItemText
                    id={`checkbox-list-label-${index}`}
                    primary={value}
                    secondary={"Last update: DD/MM/YYYY HH:SS"}
                  />
                )}
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </Layout.FlexBox>
  );
};

export default UrgencyRulesPage;
