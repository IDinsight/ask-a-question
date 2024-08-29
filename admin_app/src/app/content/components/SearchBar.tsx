import { Layout } from "@/components/Layout";
import { appColors } from "@/utils";
import { Search } from "@mui/icons-material";
import { InputAdornment, TextField } from "@mui/material";
import React from "react";

export interface SearchBarProps {
  searchTerm: string;
  setSearchTerm: React.Dispatch<React.SetStateAction<string>>;
}

export const SearchBar: React.FC<SearchBarProps> = ({ searchTerm, setSearchTerm }) => {
  return (
    <Layout.FlexBox>
      <TextField
        sx={{
          backgroundColor: appColors.white,
          borderRadius: "5px",
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
