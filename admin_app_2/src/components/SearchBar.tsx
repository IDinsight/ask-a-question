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
    <Layout.FlexBox alignItems="center">
      <TextField
        sx={{
          width: "50%",
          maxWidth: "500px",
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
    </Layout.FlexBox>
  );
};
