import React from "react";
import { Layout } from "@/components/Layout";
import {
  DEFAULT_LANGUAGE,
  LANGUAGE_OPTIONS,
  appColors,
  appStyles,
  sizes,
} from "@/utils";
import { Menu, MenuItem, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { AddCircle, Delete, InfoOutlined } from "@mui/icons-material";

const LanguageButtonBar = ({ expandable }: { expandable: boolean }) => {
  const [langList, setLangList] = React.useState(
    expandable
      ? [LANGUAGE_OPTIONS.find((l) => l.code === DEFAULT_LANGUAGE)]
      : LANGUAGE_OPTIONS
  );
  const [selectedLang, setSelectedLang] = React.useState<string>("en");
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  return (
    <Layout.FlexBox
      flexDirection={"row"}
      gap={sizes.smallGap}
      {...appStyles.alignItemsCenter}
    >
      <ToggleButtonGroup>
        {langList.map((lang, index) => (
          <ToggleButton
            key={lang?.code}
            value={lang?.code}
            size="medium"
            sx={[
              {
                border: 0,
                borderBottomColor: appColors.outline,
                borderBottomWidth: 1,
              },
              selectedLang === lang?.code && {
                borderBottomColor: appColors.primary,
                borderBottomWidth: 3,
                color: appColors.primary,
              },
            ]}
            onClick={() => setSelectedLang(lang?.code)}
          >
            <Layout.Spacer horizontal multiplier={0.5} />
            {lang?.label}
            <Layout.Spacer horizontal multiplier={0.5} />
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
      {expandable && LANGUAGE_OPTIONS.length > langList.length && (
        <AddCircle
          fontSize="small"
          onClick={(event: React.MouseEvent<SVGSVGElement, MouseEvent>) => {
            setAnchorEl(event.currentTarget as unknown as HTMLElement);
          }}
        />
      )}

      <Menu
        anchorEl={anchorEl}
        keepMounted
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
      >
        {LANGUAGE_OPTIONS.filter((l) => !langList.includes(l)).map(
          (language, index) => (
            <MenuItem
              onClick={() => {
                setLangList([...langList, language]);
                setAnchorEl(null);
              }}
              key={index}
            >
              {language.label}
            </MenuItem>
          )
        )}
      </Menu>
    </Layout.FlexBox>
  );
};

export default LanguageButtonBar;
