"use client";
import { Layout } from "@/components/Layout";
import { appColors } from "@/utils";
import { Search } from "@mui/icons-material";
import { InputAdornment, TextField } from "@mui/material";
import React from "react";

export interface SearchBarProps {
  searchTerm: string;
  setSearchTerm: React.Dispatch<React.SetStateAction<string>>;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  searchTerm,
  setSearchTerm,
}) => {
  return (
    <Layout.FlexBox
      flexDirection={"row"}
      alignItems="center"
      sx={{
        width: "70%",
        maxWidth: "600px",
        minWidth: "200px",
      }}
    >
      <TextField
        sx={{
          width: "100%",
          backgroundColor: appColors.white,
        }}
        variant="outlined"
        placeholder="Search"
        value={searchTerm}
        onChange={(e) => {
          setSearchTerm(e.target.value);
        }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Search color="secondary" />
            </InputAdornment>
          ),
        }}
      />

    </Layout.FlexBox >
  );
};
