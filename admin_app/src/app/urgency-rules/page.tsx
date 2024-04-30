"use client";
import { useState, useEffect } from "react";
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
import { Delete, Edit, Add } from "@mui/icons-material";
import { TextField, Typography, Box } from "@mui/material";
import Button from "@mui/material/Button";
import Link from "next/link";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";

const UrgencyRulesPage = () => {
  const [checked, setChecked] = useState<number[]>([]);
  const [hoveredIndex, setHoveredIndex] = useState(-1);
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

  const { token, accessLevel } = useAuth();
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

  useEffect(() => {
    apiCalls.getUrgencyRuleList(token!).then((data) => setItems(data));
  }, [token]);

  return (
    <Layout.FlexBox
      alignItems="center"
      gap={sizes.baseGap}
      py={5}
      bgcolor="white"
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          bgcolor: "background.paper",
          maxWidth: "md",
          minWidth: "sm",
        }}
      >
        <Typography sx={{ pl: 2 }} variant="h4" align="left" color="primary">
          Urgency Rules
        </Typography>
        <Layout.FlexBox
          key={"utility-strip"}
          flexDirection={"row"}
          justifyContent={"flex-right"}
          alignItems={"right"}
          sx={{
            display: "flex",
            alignSelf: "flex-end",
            px: sizes.baseGap,
          }}
          gap={sizes.baseGap}
        >
          <Button
            variant="contained"
            disabled={false}
            component={Link}
            href="/content/edit"
          >
            <Add fontSize="small" />
            New
          </Button>
          <Button
            variant="contained"
            disabled={checked.length === 0}
            component={Link}
            href="/content/edit"
            color="warning"
          >
            <Delete fontSize="small" />
            Delete
          </Button>
        </Layout.FlexBox>
        <List sx={{ width: "100%", bgcolor: "background.paper" }}>
          {items.map((value: string, index: number) => {
            const labelId = `checkbox-list-label-${value}`;

            return (
              <ListItem
                key={index}
                sx={{ borderBottom: 1, borderColor: "divider" }}
                secondaryAction={
                  index === hoveredIndex && (
                    <>
                      <IconButton
                        edge="end"
                        aria-label="delete"
                        sx={{ mx: 0.5 }}
                      >
                        <Delete fontSize="small" color="secondary" />
                      </IconButton>
                      <IconButton aria-label="edit">
                        <Edit
                          fontSize="small"
                          color="secondary"
                          onClick={() => setEditableIndex(index)}
                        />
                      </IconButton>
                    </>
                  )
                }
                disablePadding
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(-1)}
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
                      size="medium"
                      value={value}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                        handleTextChange(e.target.value, index)
                      }
                      onKeyDown={handleKeyDown}
                      onBlur={() => setEditableIndex(-1)}
                      sx={{ pr: 7, pl: 0 }}
                    />
                  ) : (
                    <ListItemText
                      id={`checkbox-list-label-${index}`}
                      primary={value}
                      secondary={"Last update: DD/MM/YYYY HH:SS"}
                      sx={{
                        pt: 0.3,
                        pb: 0.3,
                        pr: 5,
                        ".MuiListItemText-secondary": {
                          fontSize: "0.75rem",
                        },
                      }}
                    />
                  )}
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>
    </Layout.FlexBox>
  );
};

export default UrgencyRulesPage;
