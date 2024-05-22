using System.ComponentModel.DataAnnotations;
namespace DogRallyBlazorServer.Models.DTOs
{
    public class AddTrackForm
    {
        [Required]
        public DateTime Date { get; set; }

        [Required]
        public string PlaceName { get; set; }

        [Required] 
        public string CreatorName { get; set; }

        [Required] 
        public string JudgeName { get; set; }


        public string TrackImg { get; set; }

        [Required] 
        public RallyClass RallyClass { get; set; }
    }
}
