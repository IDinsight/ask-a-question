import Drawer from "@mui/material/Drawer";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import Grid from "@mui/material/Grid";

interface DrawerData {
  title: string;
  query_count: number;
  positive_votes: number;
  negative_votes: number;
  daily_query_count_avg: number;
  query_count_timeseries: { x: string; y: number }[];
  positive_votes_timeseries: { x: string; y: number }[];
  negative_votes_timeseries: { x: string; y: number }[];
  user_feedback: { timestamp: string; userQuestion: string; userFeedback: string }[];
}

interface DetailsDrawerProps {
  open: boolean;
  onClose: (open: boolean) => (event: React.KeyboardEvent | React.MouseEvent) => void;
  data: DrawerData;
}

const StatCard: React.FC<{ title: string; value: number }> = ({ title, value }) => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "left",
        justifyContent: "center",
        width: "100%",
        height: 100,
      }}
    >
      <Typography
        component="div"
        sx={{
          lineHeight: "24px",
          fontSize: "small",
          fontWeight: 300,
          color: "text.secondary",
        }}
      >
        {title}
      </Typography>
      <Typography
        variant="body2"
        sx={{ lineHeight: "16px", fontWeight: 800, fontSize: "small" }}
      >
        {value}
      </Typography>
    </Box>
  );
};

const DetailsDrawer: React.FC<DetailsDrawerProps> = ({ open, onClose, data }) => {
  return (
    <Drawer
      open={open}
      onClose={onClose(false)}
      anchor="right"
      sx={{
        [`& .MuiDrawer-paper`]: { boxSizing: "border-box" },
        zIndex: 1000,
      }}
    >
      <Box sx={{ width: 550, pt: 7, margin: 3 }}>
        <Typography
          variant="h6"
          component="div"
          sx={{ lineHeight: "24px", fontWeight: 600 }}
        >
          {data.title}
        </Typography>

        <Box
          sx={{
            display: "flex",
            flexDirection: "row",
            alignItems: "stretch",
            gap: 2,
            maxWidth: 1387,
          }}
        >
          <StatCard title="Total Sent" value={data.query_count} />
          <StatCard title="Daily Average Sent" value={data.daily_query_count_avg} />
          <StatCard title="Total Upvotes" value={data.positive_votes} />
          <StatCard title="Total Downvotes" value={data.negative_votes} />
        </Box>

        <Box
          sx={{
            height: 300,
            border: 1,
            borderColor: "secondary.main",
            borderRadius: 2,
            alignItems: "center",
            justifyContent: "center",
            display: "flex",
          }}
        >
          chart
        </Box>
        <Divider sx={{ my: 3, borderBottomWidth: 2 }} />

        <Typography
          variant="h6"
          component="div"
          sx={{ lineHeight: "24px", mb: 3, fontWeight: 600 }}
        >
          Feedback by Users
        </Typography>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            maxWidth: 1387,
            maxheight: 400,
            border: 1,
            borderColor: "secondary.main",
            borderRadius: 2,
            background: "linear-gradient(to bottom, rgba(176,198,255,0.5), #ffffff)",
            p: 2,
            mb: 3,
          }}
        >
          <Box sx={{ display: "flex", flexDirection: "row", mb: 2 }}>
            <AutoAwesomeIcon sx={{ fontSize: 25, mr: 1, color: "#9eb2e5" }} />

            <Typography
              sx={{
                lineHeight: "24px",
                fontWeight: 600,
                fontColor: "black",
                textAlign: "center",
              }}
            >
              AI Overview
            </Typography>
          </Box>

          <Typography
            sx={{
              lineHeight: "15px",
              fontWeight: 300,
              fontSize: "small",
              fontColor: "black",
              textAlign: "left",
            }}
          >
            Users are saying that the answer could elaborate on more infomation about
            specific reasons behind the purpose of the Learner Mobilisation phase. The
            answer could also provide more information on the purpose of the Learner
            Mobilisation phase.
          </Typography>
        </Box>

        <Grid
          container
          columns={13}
          sx={{
            mt: 2,
            display: "flex",
            flexDirection: "row",
            justifyContent: "center",
            borderBottom: 1,
            borderTop: 1,
            borderColor: "secondary.main",
            backgroundColor: "lightgray.main",
            fontSize: "small",
            fontWeight: 600,
            lineHeight: "32px",
          }}
        >
          <Grid md={3} sx={{ px: 1 }}>
            Timestamp
          </Grid>
          <Grid md={5} sx={{ px: 1 }}>
            User Question
          </Grid>
          <Grid md={5} sx={{ px: 1 }}>
            User Feedback
          </Grid>
        </Grid>
        {data.user_feedback.map((feedback) => (
          <Grid
            container
            columns={13}
            sx={{
              display: "flex",
              flexDirection: "row",
              justifyItems: "left",
              borderBottom: 1,
              borderColor: "secondary.main",
              fontSize: "x-small",
              lineHeight: "32px",
              overflow: "hidden",
              py: 0.5,
            }}
          >
            <Grid md={3} sx={{ px: 1, lineHeight: "20px" }}>
              {Intl.DateTimeFormat("en-ZA", {
                dateStyle: "short",
                timeStyle: "short",
              }).format(new Date(feedback.timestamp))}
            </Grid>
            <Grid
              md={5}
              sx={{
                overflow: "hidden",
                whiteSpace: "nowrap",
                textOverflow: "ellipsis",
                px: 1,
                lineHeight: "20px",
              }}
            >
              {feedback.userQuestion}
            </Grid>
            <Grid
              md={5}
              sx={{
                px: 1,
                overflow: "hidden",
                whiteSpace: "nowrap",
                textOverflow: "ellipsis",
                lineHeight: "20px",
              }}
            >
              {feedback.userFeedback}
            </Grid>
          </Grid>
        ))}
      </Box>
    </Drawer>
  );
};

export default DetailsDrawer;
