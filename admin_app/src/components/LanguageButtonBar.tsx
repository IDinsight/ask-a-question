import { Layout } from "@/components/Layout";
import { useAuth } from "@/utils/auth";
import {
  appColors,
  appStyles,
  sizes,
} from "@/utils";
import { apiCalls } from "@/utils/api";
import { AddCircle } from "@mui/icons-material";
import { Menu, MenuItem, ToggleButton, ToggleButtonGroup } from "@mui/material";
import React from "react";

interface Language {
  language_id: number;
  language_name: string;
}
interface LanguageButtonBarProps {
  expandable: boolean;
  onLanguageSelect: (language_id: number) => void;
}
const LanguageButtonBar = ({ expandable, onLanguageSelect }: LanguageButtonBarProps) => {
  const [langList, setLangList] = React.useState<Language[]>([]);
  const [selectedLang, setSelectedLang] = React.useState<number | undefined>(undefined);
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const { token } = useAuth();
  React.useEffect(() => {
    const fetchLanguages = async () => {
      try {
        const languages = await apiCalls.getLanguageList(token ?? '');
        setLangList(languages);
      } catch (error) {
        console.error('Failed to fetch languages:', error);
      }
    };

    const fetchDefaultLanguage = async () => {
      try {
        const defaultLanguage = await apiCalls.getDefaultLanguage(token ?? '');
        setSelectedLang(defaultLanguage.language_id);
        onLanguageSelect(defaultLanguage.language_id);
      } catch (error) {
        console.error('Failed to fetch default language:', error);
      }
    };

    if (token) {
      fetchLanguages();
      fetchDefaultLanguage();
    }
  }, [token, expandable]);

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleToggleButtonSelect = (language: Language) => {
    setSelectedLang(language.language_id);
    onLanguageSelect(language.language_id);
  };
  return (
    <Layout.FlexBox
      flexDirection={"row"}
      gap={sizes.smallGap}
      {...appStyles.alignItemsCenter}
    >
      <ToggleButtonGroup>
        {langList.map((lang) =>
          lang && (
            <ToggleButton
              key={lang.language_id}
              value={lang.language_id}
              size="medium"
              onClick={() => handleToggleButtonSelect(lang)}
              sx={[
                {
                  border: 0,
                  borderBottomColor: appColors.outline,
                  borderBottomWidth: 1,
                },
                selectedLang === lang?.language_id && {
                  borderBottomColor: appColors.primary,
                  borderBottomWidth: 3,
                  color: appColors.primary,
                },
              ]}
            >
              <Layout.Spacer horizontal multiplier={0.5} />
              {lang?.language_name}
              <Layout.Spacer horizontal multiplier={0.5} />
            </ToggleButton>
          ),
        )}
      </ToggleButtonGroup>
      {
        expandable && (
          <AddCircle
            fontSize="small"
            onClick={(event: React.MouseEvent<SVGSVGElement, MouseEvent>) => {
              setAnchorEl(event.currentTarget as unknown as HTMLElement);
            }}
          />
        )
      }
      <Menu
        anchorEl={anchorEl}
        keepMounted
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
      >
        {langList.filter((l) => l.language_id !== selectedLang).map(
          (language, index) => (
            <MenuItem
              key={language.language_id}
              onClick={() =>
                handleToggleButtonSelect(language)
              }

            >
              {language.language_name}
            </MenuItem>
          ),
        )}
      </Menu>
    </Layout.FlexBox >
  );
};

export default LanguageButtonBar;
