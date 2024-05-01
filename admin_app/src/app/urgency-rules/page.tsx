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

class UrgencyRule {
  urgency_rule_id: number | null;
  urgency_rule_text: string;
  updated_datetime_utc: string;
  created_datetime_utc: string;

  constructor() {
    this.urgency_rule_id = null;
    this.urgency_rule_text = "";
    this.updated_datetime_utc = "";
    this.created_datetime_utc = "";
  }
}

const UrgencyRulesPage = () => {
  const [checked, setChecked] = useState<number[]>([]);
  const [hoveredIndex, setHoveredIndex] = useState(-1);
  const [editableIndex, setEditableIndex] = useState(-1);
  const [items, setItems] = useState<UrgencyRule[]>([]);
  const [backupRuleText, setBackupRuleText] = useState("");

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
  const handleEdit = (index: number) => () => {
    setBackupRuleText(items[index].urgency_rule_text);
    setEditableIndex(index);
  };

  const handleTextChange = (ruleText: string, index: number) => {
    const newItems = [...items];
    newItems[index].urgency_rule_text = ruleText;
    setItems(newItems);
  };

  const handleKeyDown = (
    e: React.KeyboardEvent<HTMLInputElement>,
    index: number,
  ) => {
    if (e.key === "Enter") {
      if (items[index].urgency_rule_id === null) {
        apiCalls
          .addUrgencyRule(items[index].urgency_rule_text, token!)
          .then((data: UrgencyRule) => {
            const newItems = [...items];
            newItems[index] = data;
            setItems(newItems);
          });
      } else {
        apiCalls
          .updateUrgencyRule(
            items[index].urgency_rule_id!,
            items[index].urgency_rule_text,
            token!,
          )
          .then((data: UrgencyRule) => {
            const newItems = [...items];
            newItems[index] = data;
            setItems(newItems);
          });
      }
      setEditableIndex(-1);
    }
    if (e.key === "Escape") {
      restoreBackup(index);
      setEditableIndex(-1);
    }
  };

  const restoreBackup = (index: number) => {
    const newItems = [...items];
    newItems[index].urgency_rule_text = backupRuleText;
    setItems(newItems);
  };

  const createNewRecord = () => {
    const newItems = [...items];
    newItems.push(new UrgencyRule());
    setEditableIndex(newItems.length - 1);
    setItems(newItems);
  };

  const deleteItem = (index: number) => () => {
    const newItems = [...items];
    apiCalls
      .deleteUrgencyRule(items[index].urgency_rule_id!, token!)
      .then(() => {
        newItems.splice(index, 1);
        setItems(newItems);
      });
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
        <Typography sx={{ pl: 0 }} variant="h4" align="left" color="primary">
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
            onClick={() => createNewRecord()}
          >
            <Add fontSize="small" />
            New
          </Button>
        </Layout.FlexBox>
        <List sx={{ width: "100%", bgcolor: "background.paper" }}>
          {items.map((urgencyRule: UrgencyRule, index: number) => {
            const labelId = `checkbox-list-label-${index}`;
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
                        onClick={deleteItem(index)}
                      >
                        <Delete fontSize="small" color="secondary" />
                      </IconButton>
                      <IconButton aria-label="edit" onClick={handleEdit(index)}>
                        <Edit fontSize="small" color="secondary" />
                      </IconButton>
                    </>
                  )
                }
                disablePadding
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(-1)}
                onDoubleClick={handleEdit(index)}
              >
                <ListItemIcon>#{index + 1}</ListItemIcon>
                {editableIndex === index ? (
                  <TextField
                    fullWidth
                    size="medium"
                    value={urgencyRule.urgency_rule_text}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      handleTextChange(e.target.value, index)
                    }
                    onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) =>
                      handleKeyDown(e, index)
                    }
                    onBlur={() => {
                      restoreBackup(index);
                      setEditableIndex(-1);
                    }}
                    sx={{ pr: 12, pl: 0 }}
                  />
                ) : (
                  <ListItemText
                    id={`checkbox-list-label-${index}`}
                    primary={urgencyRule.urgency_rule_text}
                    secondary={
                      "Last updated: " +
                      new Date(urgencyRule.updated_datetime_utc).toLocaleString(
                        undefined,
                        {
                          day: "numeric",
                          month: "numeric",
                          year: "numeric",
                          hour: "numeric",
                          minute: "numeric",
                          hour12: true,
                        },
                      )
                    }
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
              </ListItem>
            );
          })}
        </List>
      </Box>
    </Layout.FlexBox>
  );
};

export default UrgencyRulesPage;
