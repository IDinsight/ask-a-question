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
  onMenuItemSelect?: (language_id: number) => void;
  defaultLanguageId: number;
  enabledLanguages?: number[];
  isEdit: boolean;
}
const LanguageButtonBar = ({
  expandable,
  onLanguageSelect,
  onMenuItemSelect,
  defaultLanguageId,
  enabledLanguages,
  isEdit
}: LanguageButtonBarProps) => {
  const [langList, setLangList] = React.useState<Language[]>([]);
  const [selectedLang, setSelectedLang] = React.useState<number | undefined>(defaultLanguageId);

  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const { token } = useAuth();
  const isLanguageEnabled = (languageId: number) => {
    return typeof enabledLanguages === 'undefined' || enabledLanguages.includes(languageId);
  }
  React.useEffect(() => {
    const fetchLanguages = async () => {
      try {
        const languages = await apiCalls.getLanguageList(token!);
        setLangList(languages);

        const defaultLanguage = langList
          .find(lang => lang.language_id === defaultLanguageId);
        if (defaultLanguage && !selectedLang) {
          setSelectedLang(defaultLanguageId);
          onLanguageSelect(defaultLanguageId);
        }
      } catch (error) {
        console.error('Failed to fetch languages:', error);
      }
    };

    fetchLanguages();


  }, [token, expandable, defaultLanguageId]);

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
  const handleMenuItemSelect = (language: Language) => {
    setSelectedLang(language.language_id);
    setAnchorEl(null);
    onMenuItemSelect && onMenuItemSelect(language.language_id);
  }; return (
    <Layout.FlexBox
      flexDirection={"row"}
      gap={sizes.smallGap}
      {...appStyles.alignItemsCenter}
    >
      <ToggleButtonGroup>
        {langList
          .filter(lang => !isEdit || isLanguageEnabled(lang.language_id))
          .map((lang) =>
            lang && (

              <ToggleButton
                key={lang.language_id}
                value={lang.language_id}
                size="medium"
                onClick={() => handleToggleButtonSelect(lang)}
                disabled={!isEdit && !isLanguageEnabled(lang.language_id)}
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
          )
        }
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
        {langList.filter((l) => !enabledLanguages?.includes(l.language_id)).map(
          (language, index) => (
            <MenuItem
              key={language.language_id}
              onClick={() =>
                handleMenuItemSelect(language)
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