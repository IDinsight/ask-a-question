import { TopicModelingResponse } from "../types";

const dataFromBackend: TopicModelingResponse = {
  refreshTimeStamp: "2024-08-13T15:55:50.697584Z",
  data: [
    {
      topic_id: 0,
      topic_samples: [
        {
          query_text: "test query",
          datetime_utc: "2024-08-13T15:55:50.697584Z",
        },
        {
          query_text: "test query",
          datetime_utc: "2024-08-13T15:55:50.697584Z",
        },
      ],
      topic_name: "XYZ",
      topic_popularity: 50,
    },
    {
      topic_id: 1,
      topic_samples: [
        {
          query_text: "test query 1.1",
          datetime_utc: "2024-08-13T15:55:50.697584Z",
        },
        {
          query_text: "test query 1.2",
          datetime_utc: "2024-08-13T15:55:50.697584Z",
        },
        {
          query_text: "test query 1.3",
          datetime_utc: "2024-08-13T15:55:50.697584Z",
        },
      ],
      topic_name: "ABC",
      topic_popularity: 29,
    },
  ],
};

export { dataFromBackend };
