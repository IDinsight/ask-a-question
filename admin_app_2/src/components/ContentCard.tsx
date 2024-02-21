import React from "react";
import { Card, Typography, Modal, Toolbar, Button, Box } from "@mui/material";
import { Edit, Translate } from "@mui/icons-material";
import { appColors, sizes } from "@/utils";
import { Spacers } from "./Spacers";
import ContentViewModal from "@/components/ContentModal";

const ContentCard = () => {
  const [open, setOpen] = React.useState<Boolean>(false);
  return (
    <>
      <Card
        sx={{
          alignItems: "flex-start",
          width: "300px",
          border: 1,
          borderColor: appColors.lightGrey,
          m: sizes.smallGap,
          p: sizes.baseGap,
        }}
      >
        <Typography variant="body2" alignItems={"flex-start"}>
          #134
        </Typography>

        <Typography variant="h6" alignItems={"flex-start"}>
          This is title
        </Typography>
        <Typography variant="subtitle2" color={appColors.darkGrey}>
          Last modified at 12:30 PM
        </Typography>

        <Toolbar>
          <Translate sx={{ color: appColors.outline }} />
          <Spacers.Small horizontal />
          <Typography color={appColors.outline}>en, hi</Typography>
        </Toolbar>
        <Button variant="contained" onClick={() => setOpen(true)}>
          Read
        </Button>
        <Button>
          <Edit />
          Edit
        </Button>
      </Card>
      <ContentViewModal open={open} onClose={() => setOpen(false)} />
    </>
  );
};
export default ContentCard;
