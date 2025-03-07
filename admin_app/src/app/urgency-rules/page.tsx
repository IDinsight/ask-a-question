"use client";
import { useState, useEffect, useRef } from "react";
import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  InputAdornment,
  Button,
  Tooltip,
  LinearProgress,
  Grid,
  Fab,
  Paper,
} from "@mui/material";
import { Layout } from "@/components/Layout";
import { appColors, sizes } from "@/utils";
import { Delete, Edit, Add, PlayArrow, Send } from "@mui/icons-material";
import { TextField, Typography, Box } from "@mui/material";
import {
  addUrgencyRule,
  updateUrgencyRule,
  getUrgencyRuleList,
  deleteUrgencyRule,
} from "./api";
import { useAuth } from "@/utils/auth";
import { UDSidebar } from "./components/UDSidebar";

class UrgencyRule {
  urgency_rule_id: number | null = null;
  urgency_rule_text: string = "";
  updated_datetime_utc: string = "";
  created_datetime_utc: string = "";
}

const UrgencyRulesPage = () => {
  const [saving, setSaving] = useState(false);
  const lastItemRef = useRef<HTMLLIElement>(null);
  const [hoveredIndex, setHoveredIndex] = useState(-1);
  const [editableIndex, setEditableIndex] = useState(-1);
  const [items, setItems] = useState<UrgencyRule[]>([]);
  const [backupRuleText, setBackupRuleText] = useState("");
  const [currAccessLevel, setCurrAccessLevel] = useState("readonly");
  const { token, accessLevel, userRole } = useAuth();
  const handleEdit = (index: number) => () => {
    setBackupRuleText(items[index].urgency_rule_text);
    setEditableIndex(index);
  };

  const handleTextChange = (ruleText: string, index: number) => {
    const newItems = [...items];
    newItems[index].urgency_rule_text = ruleText;
    setItems(newItems);
  };

  const addOrUpdateItem = (index: number) => {
    setSaving(true);
    if (items[index].urgency_rule_id === null) {
      addUrgencyRule(items[index].urgency_rule_text, token!).then(
        (data: UrgencyRule) => {
          const newItems = [...items];
          newItems[index] = data;
          setItems(newItems);
          setSaving(false);
        },
      );
    } else {
      updateUrgencyRule(
        items[index].urgency_rule_id!,
        items[index].urgency_rule_text,
        token!,
      ).then((data: UrgencyRule) => {
        const newItems = [...items];
        newItems[index] = data;
        setItems(newItems);
        setSaving(false);
      });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === "Enter") {
      addOrUpdateItem(index);
      setEditableIndex(-1);
    }
    if (e.key === "Escape") {
      restoreBackup(index);
      setEditableIndex(-1);
      if (items[index].urgency_rule_id === null) {
        const newItems = [...items];
        newItems.splice(index, 1);
        setItems(newItems);
      }
    }
  };

  const restoreBackup = (index: number) => {
    const newItems = [...items];
    newItems[index].urgency_rule_text = backupRuleText;
    setBackupRuleText("");
    setItems(newItems);
  };

  const createNewRecord = () => {
    const newItems = [...items];
    if (items.length > 0 && items[items.length - 1].urgency_rule_id === null) {
      setEditableIndex(newItems.length - 1);
      return;
    } else {
      newItems.push(new UrgencyRule());
      setEditableIndex(newItems.length - 1);
      setItems(newItems);
      if (lastItemRef.current) {
        lastItemRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  const deleteItem = (index: number) => () => {
    const newItems = [...items];
    if (items[index].urgency_rule_id === null) {
      newItems.splice(index, 1);
      setItems(newItems);
      return;
    }
    deleteUrgencyRule(items[index].urgency_rule_id!, token!).then(() => {
      newItems.splice(index, 1);
      setItems(newItems);
    });
  };

  const onBlur = (index: number) => {
    if (items[index].urgency_rule_id !== null) {
      restoreBackup(index);
      setEditableIndex(-1);
    }
  };

  useEffect(() => {
    if (token) {
      getUrgencyRuleList(token)
        .then((data) => setItems(data))
        .catch((error) => {
          console.error(error);
        });
      setCurrAccessLevel(accessLevel);
    } else {
      setItems([]);
    }
  }, [token, accessLevel]);

  const [openSidebar, setOpenSideBar] = useState(false);
  const handleSidebarToggle = () => {
    setOpenSideBar(!openSidebar);
  };
  const handleSidebarClose = () => {
    setOpenSideBar(false);
  };

  const sidebarGridWidth = openSidebar ? 5 : 0;
  const editAccess = userRole === "admin";
  return (
    <Grid container sx={{ height: "100%" }}>
      <Grid
        item
        xs={12}
        sm={12}
        md={12 - sidebarGridWidth}
        lg={12 - sidebarGridWidth + 1}
        sx={{
          display: openSidebar ? { xs: "none", sm: "none", md: "block" } : "block",
          height: "100%",
          paddingTop: 5,
          paddingInline: 4,
        }}
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            height: "100%",
          }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              height: "100%",
              width: "100%",
              maxWidth: "lg",
              minWidth: "sm",
            }}
          >
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                paddingBottom: 2,
                gap: 2,
              }}
            >
              <Typography variant="h4" align="left" color="primary">
                Urgency Detection
              </Typography>
              <Typography variant="body1" align="left" color={appColors.darkGrey}>
                Add, edit, and test urgency rules. Messages sent to the urgency
                detection service will be flagged as urgent if any of the rules apply to
                the message.
              </Typography>
            </Box>
            <Box
              sx={{
                display: "flex",
                flexDirection: "row",
                justifyContent: "flex-end",
                paddingBottom: 2,
              }}
            >
              <Tooltip title="Add new urgency rule">
                <>
                  <Button
                    variant="contained"
                    disabled={saving || !editAccess}
                    onClick={() => createNewRecord()}
                    startIcon={<Add fontSize="small" />}
                  >
                    New
                  </Button>
                </>
              </Tooltip>
            </Box>
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                flexGrow: 1,
                minHeight: 0,
              }}
            >
              <Paper
                elevation={0}
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  flexGrow: 1,
                  overflowY: "auto",
                  paddingTop: 1,
                  paddingBottom: 10,
                  paddingInline: 3,
                  border: 0.5,
                  borderColor: "lightgrey",
                }}
              >
                {items.length === 0 ? (
                  <Box
                    sx={{
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "center",
                      alignItems: "center",
                      width: "100%",
                      padding: sizes.doubleBaseGap,
                    }}
                  >
                    <p>
                      <Typography variant="h6" color={appColors.darkGrey}>
                        No rules yet.
                      </Typography>
                    </p>
                    <p>
                      <Typography variant="body1" color={appColors.darkGrey}>
                        Click the NEW button to add your first rule.
                      </Typography>
                    </p>
                  </Box>
                ) : (
                  <List>
                    {items.map((urgencyRule: UrgencyRule, index: number) => {
                      const isLastItem = index === items.length - 1;
                      return (
                        <ListItem
                          key={index}
                          ref={isLastItem ? lastItemRef : null}
                          sx={{
                            borderBottom: 1,
                            borderColor: "divider",
                            marginBottom: 2,
                            overflowWrap: "break-word",
                            hyphens: "auto",
                            whiteSpace: "pre-wrap",
                          }}
                          secondaryAction={
                            index === hoveredIndex &&
                            currAccessLevel == "fullaccess" && (
                              <>
                                <IconButton
                                  edge="end"
                                  aria-label="delete"
                                  sx={{ marginRight: 0.5 }}
                                  onClick={deleteItem(index)}
                                  disabled={!editAccess}
                                >
                                  <Delete fontSize="small" color="primary" />
                                </IconButton>
                                <IconButton
                                  aria-label="edit"
                                  onClick={handleEdit(index)}
                                  disabled={!editAccess}
                                >
                                  <Edit fontSize="small" color="primary" />
                                </IconButton>
                              </>
                            )
                          }
                          disablePadding
                          onMouseEnter={() => setHoveredIndex(index)}
                          onMouseLeave={() => setHoveredIndex(-1)}
                          onDoubleClick={editAccess ? handleEdit(index) : () => {}}
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
                                onBlur(index);
                              }}
                              sx={{
                                paddingRight: 12,
                                paddingLeft: 0,
                                marginBottom: 1,
                              }}
                              InputProps={{
                                style: { backgroundColor: "white" },
                                endAdornment: (
                                  <InputAdornment
                                    position="end"
                                    sx={{ paddingRight: 2 }}
                                  >
                                    <IconButton
                                      onMouseDown={() => {
                                        addOrUpdateItem(index);
                                        setEditableIndex(-1);
                                      }}
                                      edge="end"
                                    >
                                      <Send fontSize="small" />
                                    </IconButton>
                                  </InputAdornment>
                                ),
                              }}
                            />
                          ) : (
                            <ListItemText
                              id={`checkbox-list-label-${index}`}
                              primary={urgencyRule.urgency_rule_text}
                              secondary={
                                urgencyRule.updated_datetime_utc ? (
                                  "Last updated: " +
                                  new Date(
                                    urgencyRule.updated_datetime_utc,
                                  ).toLocaleString(undefined, {
                                    day: "numeric",
                                    month: "numeric",
                                    year: "numeric",
                                    hour: "numeric",
                                    minute: "numeric",
                                    hour12: true,
                                  })
                                ) : (
                                  <Typography component="span">
                                    <Layout.Spacer multiplier={0.8} />
                                    <LinearProgress color="secondary" />
                                  </Typography>
                                )
                              }
                              sx={{
                                paddingTop: 0.3,
                                paddingBottom: 0.3,
                                paddingRight: 12,
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
                )}
              </Paper>
              <Fab
                variant="extended"
                size="medium"
                disabled={openSidebar}
                sx={{
                  bgcolor: "orange",
                  alignSelf: "flex-end",
                  pr: 2,
                  marginTop: 2,
                  marginBottom: 3,
                }}
                onClick={handleSidebarToggle}
              >
                <PlayArrow />
                <Layout.Spacer horizontal multiplier={0.3} />
                Test
              </Fab>
            </Box>
          </Box>
        </Box>
      </Grid>
      <Grid
        item
        xs={openSidebar ? 12 : 0}
        sm={openSidebar ? 12 : 0}
        md={sidebarGridWidth}
        lg={sidebarGridWidth - 1}
        sx={{
          display: openSidebar ? "block" : "none",
        }}
      >
        <UDSidebar closeSidebar={handleSidebarClose} />
      </Grid>
    </Grid>
  );
};

export default UrgencyRulesPage;
